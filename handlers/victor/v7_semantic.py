
from __future__ import annotations
"""Victor v7.0 TITAN — Semantic Index (MinHash LSH)"""

from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple

from .nlp import PersianNLP

# ═══════════════════════════════════════════════════════════════════
# 6. SEMANTIC INDEX — v7 MinHash Locality-Sensitive Hashing
# ═══════════════════════════════════════════════════════════════════

class SemanticIndex:
    """
    v7: MinHash-based semantic similarity index.
    Uses locality-sensitive hashing for fast approximate nearest-neighbor search.
    No external ML dependencies — pure algorithmic.
    """

    def __init__(self, num_hashes: int = 128, bands: int = 16) -> None:
        self.num_hashes = num_hashes
        self.bands = bands
        self.rows_per_band = num_hashes // bands
        self._signatures: Dict[str, List[int]] = {}  # doc_id → minhash signature
        self._buckets: Dict[int, Dict[int, Set[str]]] = {
            b: defaultdict(set) for b in range(bands)
        }
        self._large_prime = 4294967311  # prime > 2^32
        self._hash_params: List[Tuple[int, int]] = [
            (hash(f"a_{i}") % self._large_prime, hash(f"b_{i}") % self._large_prime)
            for i in range(num_hashes)
        ]

    def _compute_signature(self, shingles: Set[str]) -> List[int]:
        """Compute MinHash signature for a set of shingles."""
        if not shingles:
            return [0] * self.num_hashes
        signature = []
        for a, b in self._hash_params:
            min_hash = float('inf')
            for shingle in shingles:
                h = (a * hash(shingle) + b) % self._large_prime
                min_hash = min(min_hash, h)
            signature.append(min_hash)
        return signature

    def _text_to_shingles(self, text: str, k: int = 3) -> Set[str]:
        """Convert text to character k-shingles."""
        text = PersianNLP.normalize(text.lower())
        tokens = PersianNLP.tokenize(text)
        # Both character and word shingles for better coverage
        char_shingles = {text[i:i+k] for i in range(len(text) - k + 1)} if len(text) >= k else {text}
        word_shingles = set()
        for i in range(len(tokens)):
            word_shingles.add(tokens[i])
            if i + 1 < len(tokens):
                word_shingles.add(f"{tokens[i]}_{tokens[i+1]}")
        return char_shingles | word_shingles

    def index_document(self, doc_id: str, text: str) -> Any:
        """Add a document to the index."""
        shingles = self._text_to_shingles(text)
        signature = self._compute_signature(shingles)
        self._signatures[doc_id] = signature
        # LSH banding
        for band_idx in range(self.bands):
            start = band_idx * self.rows_per_band
            end = start + self.rows_per_band
            band_hash = hash(tuple(signature[start:end]))
            self._buckets[band_idx][band_hash].add(doc_id)

    def remove_document(self, doc_id: str) -> None:
        """Remove a document from the index."""
        if doc_id not in self._signatures:
            return
        sig = self._signatures[doc_id]
        for band_idx in range(self.bands):
            start = band_idx * self.rows_per_band
            end = start + self.rows_per_band
            band_hash = hash(tuple(sig[start:end]))
            self._buckets[band_idx][band_hash].discard(doc_id)
        del self._signatures[doc_id]

    def find_similar(self, text: str, top_k: int = 10, threshold: float = 0.3) -> List[Tuple[str, float]]:
        """Find similar documents using LSH + MinHash similarity."""
        shingles = self._text_to_shingles(text)
        query_sig = self._compute_signature(shingles)

        # Candidate generation via LSH
        candidates: Set[str] = set()
        for band_idx in range(self.bands):
            start = band_idx * self.rows_per_band
            end = start + self.rows_per_band
            band_hash = hash(tuple(query_sig[start:end]))
            candidates |= self._buckets[band_idx].get(band_hash, set())

        # Compute actual Jaccard similarity for candidates
        results = []
        for doc_id in candidates:
            if doc_id not in self._signatures:
                continue
            doc_sig = self._signatures[doc_id]
            # Estimate Jaccard similarity
            matches = sum(1 for a, b in zip(query_sig, doc_sig) if a == b)
            similarity = matches / self.num_hashes
            if similarity >= threshold:
                results.append((doc_id, similarity))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def stats(self) -> Dict[str, Any]:
        return {
            "indexed_documents": len(self._signatures),
            "num_hashes": self.num_hashes,
            "bands": self.bands,
        }


