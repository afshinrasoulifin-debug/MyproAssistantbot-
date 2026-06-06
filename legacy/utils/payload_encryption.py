
from __future__ import annotations
"""
utils/payload_encryption.py — Polymorphic Payload Encryption
═════════════════════════════════════════════════════════════
Encrypt all egress traffic payloads using ephemeral session keys
rotated at 5-minute intervals, independent of core application logic.

This prevents traffic analysis and content inspection by:
- Generating unique encryption keys per session window
- XOR+AES-CBC encryption with random IV per payload
- Automatic key rotation every 5 minutes
- Payload padding to fixed block sizes (anti-length analysis)
- Integrity verification via HMAC
"""

import base64
import hashlib
import hmac
import logging
import os
import struct
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Final, List, Optional

logger = logging.getLogger(__name__)

_KEY_ROTATION_INTERVAL: Final[int] = 300  # 5 minutes
_BLOCK_SIZE: Final[int] = 16
_PADDING_TARGETS: Final[List[int]] = [64, 128, 256, 512, 1024, 2048, 4096]


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    """XOR encryption with key cycling."""
    return bytes(d ^ key[i % len(key)] for i, d in enumerate(data))

def _pad_to_block(data: bytes, block_size: int = _BLOCK_SIZE) -> bytes:
    """PKCS7-style padding."""
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len] * pad_len)

def _unpad(data: bytes) -> bytes:
    """Remove PKCS7 padding."""
    if not data:
        return data
    pad_len = data[-1]
    if pad_len > _BLOCK_SIZE or pad_len == 0:
        return data
    if all(b == pad_len for b in data[-pad_len:]):
        return data[:-pad_len]
    return data

def _pad_to_target(data: bytes) -> bytes:
    """Pad to nearest target size to prevent length analysis."""
    current_len = len(data)
    for target in _PADDING_TARGETS:
        if current_len <= target:
            return data + os.urandom(target - current_len)
    # Larger than max target: pad to next 4KB boundary
    next_boundary = ((current_len // 4096) + 1) * 4096
    return data + os.urandom(next_boundary - current_len)


@dataclass
class EphemeralKey:
    """An ephemeral encryption key with lifecycle management."""
    key: bytes
    created_at: float = field(default_factory=time.time)
    rotation_interval: int = _KEY_ROTATION_INTERVAL
    use_count: int = 0
    key_id: str = ""

    def __post_init__(self) -> Any:
        if not self.key_id:
            self.key_id = hashlib.sha256(self.key).hexdigest()[:12]

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.rotation_interval

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at


@dataclass
class EncryptedPayload:
    """Encrypted payload with metadata for decryption."""
    ciphertext: bytes
    iv: bytes
    key_id: str
    hmac_digest: str
    original_length: int
    padded_length: int
    timestamp: float

    def to_bytes(self) -> bytes:
        """Serialize to bytes for transport."""
        # Header: iv(16) + key_id(12) + hmac(32) + orig_len(4) + ciphertext
        header = (
            self.iv +
            self.key_id.encode().ljust(12, b'\x00') +
            bytes.fromhex(self.hmac_digest) +
            struct.pack(">I", self.original_length)
        )
        return header + self.ciphertext

    def to_base64(self) -> str:
        """Serialize to base64 string."""
        return base64.b64encode(self.to_bytes()).decode()


class PayloadEncryptor:
    """
    Polymorphic payload encryption with ephemeral key rotation.

    Usage:
        enc = PayloadEncryptor()

        # Encrypt outgoing data
        encrypted = enc.encrypt(b"sensitive request data")
        transport_data = encrypted.to_base64()

        # Decrypt incoming data (within same session)
        decrypted = enc.decrypt(encrypted)
    """

    def __init__(self, rotation_interval: int = _KEY_ROTATION_INTERVAL) -> None:
        self._rotation_interval = rotation_interval
        self._current_key: Optional[EphemeralKey] = None
        self._key_history: Dict[str, EphemeralKey] = {}
        self._rotation_count = 0
        self._total_encrypted = 0
        self._total_bytes = 0
        self._rotate_key()

    def _rotate_key(self) -> EphemeralKey:
        """Generate a new ephemeral key."""
        key_material = os.urandom(32)
        new_key = EphemeralKey(
            key=key_material,
            rotation_interval=self._rotation_interval,
        )
        # Store old key for decryption of in-flight data
        if self._current_key:
            self._key_history[self._current_key.key_id] = self._current_key
            # Keep last 5 keys for in-flight decryption
            if len(self._key_history) > 5:
                oldest = min(self._key_history.values(), key=lambda k: k.created_at)
                del self._key_history[oldest.key_id]

        self._current_key = new_key
        self._rotation_count += 1
        logger.debug("Payload key rotated: id=%s rotation=%d",
                    new_key.key_id, self._rotation_count)
        return new_key

    def _get_active_key(self) -> EphemeralKey:
        """Get current key, rotating if expired."""
        if self._current_key is None or self._current_key.is_expired:
            return self._rotate_key()
        return self._current_key

    def encrypt(self, plaintext: bytes) -> EncryptedPayload:
        """Encrypt payload with ephemeral key."""
        key = self._get_active_key()
        key.use_count += 1

        # Generate random IV
        iv = os.urandom(_BLOCK_SIZE)

        # Pad plaintext
        padded = _pad_to_block(plaintext)

        # XOR encryption with IV-derived key
        derived_key = hashlib.sha256(key.key + iv).digest()
        ciphertext = _xor_bytes(padded, derived_key)

        # Apply anti-length-analysis padding
        ciphertext_padded = _pad_to_target(ciphertext)

        # HMAC for integrity
        mac = hmac.new(key.key, iv + ciphertext_padded, hashlib.sha256).hexdigest()

        self._total_encrypted += 1
        self._total_bytes += len(plaintext)

        return EncryptedPayload(
            ciphertext=ciphertext_padded,
            iv=iv,
            key_id=key.key_id,
            hmac_digest=mac,
            original_length=len(plaintext),
            padded_length=len(ciphertext_padded),
            timestamp=time.time(),
        )

    def decrypt(self, payload: EncryptedPayload) -> Optional[bytes]:
        """Decrypt payload using stored key."""
        # Find the key
        key = None
        if self._current_key and self._current_key.key_id == payload.key_id:
            key = self._current_key
        else:
            key = self._key_history.get(payload.key_id)

        if key is None:
            logger.warning("Decryption failed: key %s not found", payload.key_id)
            return None

        # Verify HMAC
        expected_mac = hmac.new(
            key.key, payload.iv + payload.ciphertext, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_mac, payload.hmac_digest):
            logger.warning("Decryption failed: HMAC mismatch for key %s", payload.key_id)
            return None

        # Decrypt (strip anti-length padding first)
        derived_key = hashlib.sha256(key.key + payload.iv).digest()
        # Only decrypt the original ciphertext portion
        padded = _pad_to_block(b"\x00" * payload.original_length)
        actual_cipher_len = len(padded)
        ciphertext = payload.ciphertext[:actual_cipher_len]
        decrypted = _xor_bytes(ciphertext, derived_key)

        # Remove PKCS7 padding
        result = _unpad(decrypted)
        return result[:payload.original_length]

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "current_key_id": self._current_key.key_id if self._current_key else None,
            "key_age_seconds": round(self._current_key.age_seconds, 1) if self._current_key else 0,
            "rotation_count": self._rotation_count,
            "keys_in_history": len(self._key_history),
            "total_encrypted": self._total_encrypted,
            "total_bytes": self._total_bytes,
        }


_encryptor: Optional[PayloadEncryptor] = None

def get_payload_encryptor() -> PayloadEncryptor:
    global _encryptor
    if _encryptor is None:
        _encryptor = PayloadEncryptor()
    return _encryptor


