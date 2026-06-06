
"""
web_search_pkg/sim_hash.py — SimHash
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class SimHash:
    """
    SimHash implementation for near-duplicate text detection.

    Uses 64-bit fingerprints. Two documents with Hamming distance
    ≤ 3 are considered near-duplicates.
    """

    HASH_BITS = 64

    @classmethod
    def compute(cls, text: str) -> int:
        """Compute SimHash fingerprint for text."""
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return 0

        # Generate weighted feature vector
        v = [0] * cls.HASH_BITS
        for token in tokens:
            token_hash = cls._hash_token(token)
            for i in range(cls.HASH_BITS):
                if token_hash & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1

        # Convert to fingerprint
        fingerprint = 0
        for i in range(cls.HASH_BITS):
            if v[i] >= 0:
                fingerprint |= (1 << i)

        return fingerprint

    @classmethod
    def _hash_token(cls, token: str) -> int:
        """Hash a token to a 64-bit integer."""
        h = hashlib.md5(token.encode()).hexdigest()
        return int(h[:16], 16)

    @classmethod
    def hamming_distance(cls, hash1: int, hash2: int) -> int:
        """Compute Hamming distance between two SimHash values."""
        xor = hash1 ^ hash2
        return bin(xor).count("1")

    @classmethod
    def is_near_duplicate(cls, hash1: int, hash2: int,
                          threshold: int = 3) -> bool:
        """Check if two SimHash values indicate near-duplicates."""
        return cls.hamming_distance(hash1, hash2) <= threshold


# ═══════════════════════════════════════════════════════════════════
# BM25 Ranking
# ═══════════════════════════════════════════════════════════════════



