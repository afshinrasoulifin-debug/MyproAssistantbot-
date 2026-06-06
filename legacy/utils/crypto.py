
"""
utils/crypto.py — DEPRECATED v17.3
═══════════════════════════════════
⚠️ DEPRECATED: This module is deprecated since v17.3.
All new code should use utils/kms_enforcer.py for key management
and utils/payload_encryption.py for encryption.

Legacy encrypt_dict/decrypt_dict maintained for backward compatibility
with data_store.py. Will be removed in v18.0.
"""
import warnings
from typing import Any
warnings.warn(
    "utils/crypto.py is deprecated since v17.3. "
    "Use utils/kms_enforcer.py and utils/payload_encryption.py instead.",
    DeprecationWarning,
    stacklevel=2,
)
from arki_project.utils.crypto_engine import aes_encrypt as encrypt, aes_decrypt as decrypt, hash_data, hmac_verify as verify_hash, random_token as generate_key  # noqa: F401

import hashlib
import json
import base64
import logging

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

_KEY = None

def _get_key() -> Any:
    """v17.3: No insecure defaults. Redirects to KMS enforcer."""
    global _KEY
    if _KEY is None:
        # Try KMS enforcer first
        try:
            from arki_project.utils.kms_enforcer import get_kms_enforcer
            enforcer = get_kms_enforcer()
            kms_key = enforcer.get_key("encryption", source="crypto.py")
            if kms_key:
                _KEY = hashlib.sha256(kms_key.encode()).digest()
                return _KEY
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)
        # Fallback: require ENCRYPTION_KEY env var
        import os
        secret = os.environ.get("ENCRYPTION_KEY", "")
        if not secret:
            logger.critical(
                "⛔ ENCRYPTION_KEY not set and KMS unavailable. "
                "Generating ephemeral key — data will NOT survive restart."
            )
            import secrets as _sec
            secret = _sec.token_hex(32)
        if secret in ("arki-default-key-DO-NOT-USE-IN-PRODUCTION", "changeme"):
            raise RuntimeError(
                "⛔ Insecure default ENCRYPTION_KEY detected. "
                "Set a cryptographically strong key via .env or KMS."
            )
        _KEY = hashlib.sha256(secret.encode()).digest()
    return _KEY


def encrypt_dict(data: dict) -> str:
    """Encrypt a dict to a base64 string (simple XOR for demo)."""
    raw = json.dumps(data, ensure_ascii=False).encode()
    key = _get_key()
    encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    return base64.b64encode(encrypted).decode()


def decrypt_dict(token: str) -> dict:
    """Decrypt a base64 string back to dict."""
    encrypted = base64.b64decode(token)
    key = _get_key()
    decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(encrypted))
    return json.loads(decrypted.decode())


