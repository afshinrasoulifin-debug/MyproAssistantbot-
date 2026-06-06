
"""
infrastructure/core/secure_memory.py — Encrypted Memory-only Identity Store v1.0
═══════════════════════════════════════════════════════════════════════════
Stores sensitive TITANIUM identities, cookies, and session keys in encrypted 
memory. No filesystem traces. Zero persistence across reboots for safety.
"""

import os
import json
import base64
import logging
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger("arki.infra.secure_memory")

class SecureMemoryStore:
    """
    Volatile, encrypted memory store for sensitive session data.
    """
    def __init__(self) -> None:
        # Generate a unique key for this runtime session only
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(os.urandom(32)))
        self._fernet = Fernet(key)
        self._store: Dict[str, bytes] = {}
        logger.info("🔒 SecureMemoryStore initialized (Volatile/Encrypted)")

    def set(self, key: str, value: Any) -> None:
        """Encrypt and store a value in memory."""
        data = json.dumps(value).encode()
        encrypted = self._fernet.encrypt(data)
        self._store[key] = encrypted

    def get(self, key: str) -> Optional[Any]:
        """Retrieve and decrypt a value from memory."""
        encrypted = self._store.get(key)
        if not encrypted:
            return None
        try:
            decrypted = self._fernet.decrypt(encrypted)
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error("Failed to decrypt secure memory key '%s': %s", key, e)
            return None

    def delete(self, key: str) -> None:
        """Remove a key from memory."""
        if key in self._store:
            del self._store[key]

    def clear(self) -> None:
        """Wipe the entire memory store."""
        self._store.clear()
        logger.warning("🧹 SecureMemoryStore wiped")

# Global singleton
secure_memory = SecureMemoryStore()


