
from __future__ import annotations
"""
tg_bot/utils/titanium/crypto.py — CSPRNG & HMAC Utilities v10.3.1
═══════════════════════════════════════════════════════════
Replaces all `random.random()` / `random.choice()` with
cryptographically secure alternatives.

Ported from: TITANIUM ZKI utils/crypto.ts
"""


import hmac
import hashlib
import os
from typing import Sequence, TypeVar

T = TypeVar("T")


def csprng_int(lo: int, hi: int) -> int:
    """Cryptographically secure random integer in [lo, hi]."""
    if lo >= hi:
        return lo
    span = hi - lo + 1
    # Rejection sampling to avoid modulo bias
    bits_needed = (span - 1).bit_length()
    byte_count = (bits_needed + 7) // 8
    mask = (1 << bits_needed) - 1

    for _ in range(64):  # safety bound
        raw = int.from_bytes(os.urandom(byte_count), "big") & mask
        if raw < span:
            return lo + raw
    # Fallback (extremely unlikely)
    return lo + int.from_bytes(os.urandom(byte_count), "big") % span


def csprng_float() -> float:
    """Cryptographically secure float in [0.0, 1.0)."""
    # 53-bit mantissa for full double precision
    raw = int.from_bytes(os.urandom(7), "big") >> 3
    return raw / (1 << 53)


def csprng_choice(seq: Sequence[T]) -> T:
    """Cryptographically secure random choice from a sequence."""
    if not seq:
        raise IndexError("csprng_choice from empty sequence")
    return seq[csprng_int(0, len(seq) - 1)]


def csprng_weighted_choice(items: Sequence[T], weights: Sequence[float]) -> T:
    """
    CSPRNG weighted selection.

    Unlike random.choices() which uses Mersenne Twister (predictable),
    this uses os.urandom for unpredictable selection.
    """
    if len(items) != len(weights):
        raise ValueError("items and weights must have same length")
    if not items:
        raise IndexError("csprng_weighted_choice from empty sequence")

    total = sum(weights)
    if total <= 0:
        return csprng_choice(items)

    r = csprng_float() * total
    cumulative = 0.0
    for item, weight in zip(items, weights):
        cumulative += weight
        if r < cumulative:
            return item
    return items[-1]  # rounding safety


def hmac_sign(key: bytes, data: bytes) -> str:
    """HMAC-SHA256 sign → hex string."""
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def hmac_verify(key: bytes, data: bytes, signature: str) -> bool:
    """
    Constant-time HMAC-SHA256 verification.

    Uses hmac.compare_digest() which is immune to timing attacks
    (unlike == which short-circuits on first mismatch).
    """
    expected = hmac.new(key, data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def secure_hex(n_bytes: int = 16) -> str:
    """Generate a secure random hex string."""
    return os.urandom(n_bytes).hex()


def secure_request_id() -> str:
    """Generate a unique request ID (24 hex chars)."""
    return os.urandom(12).hex()


# ══════════════════════════════════════════════════════════════
# v10.4 Advanced Cryptographic Operations
# ══════════════════════════════════════════════════════════════

import time as _time
import json as _json
import base64 as _base64


class KeyRotator:
    """Automatic key rotation with grace period for old keys."""

    def __init__(self, rotation_interval: float = 86400.0) -> None:
        self._rotation_interval = rotation_interval
        self._current_key = secure_hex(32)
        self._previous_key: str | None = None
        self._rotated_at = _time.time()

    @property
    def current_key(self) -> str:
        if _time.time() - self._rotated_at > self._rotation_interval:
            self.rotate()
        return self._current_key

    def rotate(self) -> str:
        self._previous_key = self._current_key
        self._current_key = secure_hex(32)
        self._rotated_at = _time.time()
        return self._current_key

    def verify_with_rotation(self, key: str) -> bool:
        """Verify key against current or previous (grace period)."""
        import hmac as _hmac
        if _hmac.compare_digest(key, self._current_key):
            return True
        if self._previous_key and _hmac.compare_digest(key, self._previous_key):
            return True
        return False


def generate_secure_token(
    payload: dict,
    secret: bytes,
    ttl_seconds: int = 3600,
) -> str:
    """Generate a time-limited secure token (not JWT — simpler and safer)."""
    data = {
        "p": payload,
        "exp": int(_time.time()) + ttl_seconds,
        "iat": int(_time.time()),
        "jti": secure_hex(8),
    }
    raw = _json.dumps(data, separators=(",", ":"), sort_keys=True)
    encoded = _base64.urlsafe_b64encode(raw.encode()).decode()
    sig = hmac_sign(secret, raw.encode())
    return f"{encoded}.{sig}"


def verify_secure_token(token: str, secret: bytes) -> dict | None:
    """Verify and decode a secure token. Returns None if invalid/expired."""
    try:
        parts = token.rsplit(".", 1)
        if len(parts) != 2:
            return None
        encoded, sig = parts
        raw = _base64.urlsafe_b64decode(encoded).decode()
        if not hmac_verify(secret, raw.encode(), sig):
            return None
        data = _json.loads(raw)
        if data.get("exp", 0) < _time.time():
            return None
        return data.get("p")
    except Exception:
        return None


def derive_key(password: str, salt: bytes | None = None, iterations: int = 100_000) -> tuple[bytes, bytes]:
    """PBKDF2 key derivation."""
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return key, salt


