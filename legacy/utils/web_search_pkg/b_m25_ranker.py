
"""
web_search_pkg/b_m25_ranker.py — BM25Ranker
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class BM25Ranker:
    """
    BM25 (Okapi BM25) ranking algorithm.

    Industry-standard probabilistic relevance ranking.
    Used by Elasticsearch, Lucene, etc.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.documents: List[List[str]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0
        self.idf_cache: Dict[str, float] = {}
        self.doc_freqs: Dict[str, int] = {}
        self.n_docs: int = 0

    def fit(self, documents: List[str]) -> None:
        """Index a collection of documents."""
        self.documents = [
            re.findall(r"\w+", doc.lower()) for doc in documents
        ]
        self.doc_lengths = [len(d) for d in self.documents]
        self.n_docs = len(self.documents)
        self.avg_doc_length = (
            sum(self.doc_lengths) / max(1, self.n_docs)
        )

        # Compute document frequencies
        self.doc_freqs = {}
        for doc in self.documents:
            unique_terms = set(doc)
            for term in unique_terms:
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

        # Precompute IDF
        for term, df in self.doc_freqs.items():
            self.idf_cache[term] = math.log(
                (self.n_docs - df + 0.5) / (df + 0.5) + 1
            )

    def score(self, query: str, doc_idx: int) -> float:
        """Score a single document against a query."""
        if doc_idx >= len(self.documents):
            return 0.0

        query_terms = re.findall(r"\w+", query.lower())
        doc = self.documents[doc_idx]
        doc_len = self.doc_lengths[doc_idx]
        term_freqs = Counter(doc)

        score = 0.0
        for term in query_terms:
            if term not in self.idf_cache:
                continue
            tf = term_freqs.get(term, 0)
            idf = self.idf_cache[term]
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (
                1 - self.b + self.b * doc_len / max(1, self.avg_doc_length)
            )
            score += idf * (numerator / max(1e-10, denominator))

        return score

    def rank(self, query: str, top_n: int = 10) -> List[Tuple[int, float]]:
        """Rank all documents by relevance to query."""
        scores = [
            (i, self.score(query, i))
            for i in range(self.n_docs)
        ]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_n]


# ═══════════════════════════════════════════════════════════════════
# Content Extractor
# ═══════════════════════════════════════════════════════════════════



