
"""
memory_store_pkg/semantic_index.py — SemanticIndex
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class SemanticIndex:
    """Simple keyword-based semantic search (no ML deps required)."""

    def __init__(self):
        self._index: dict[str, set[str]] = {}  # keyword -> set of memory_ids

    def index_content(self, memory_id: str, content: str):
        """Index content by keywords for semantic retrieval."""
        import re
        words = set(re.findall(r'\b\w{3,}\b', content.lower()))
        for w in words:
            if w not in self._index:
                self._index[w] = set()
            self._index[w].add(memory_id)

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Search by keyword overlap (TF-IDF-like scoring)."""
        import re, math
        query_words = set(re.findall(r'\b\w{3,}\b', query.lower()))
        if not query_words:
            return []

        scores: dict[str, float] = {}
        total_docs = len(set.union(*self._index.values())) if self._index else 1

        for word in query_words:
            if word not in self._index:
                continue
            matching = self._index[word]
            idf = math.log(total_docs / (len(matching) + 1)) + 1
            for mid in matching:
                scores[mid] = scores.get(mid, 0) + idf

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]




