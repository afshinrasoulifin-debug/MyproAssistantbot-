
"""
web_search_pkg/deep_search_result.py — DeepSearchResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class DeepSearchResult:
    """Aggregated deep search result."""
    query: str
    results: List[SearchResult] = field(default_factory=list)
    total_found: int = 0
    engines_used: List[SearchEngine] = field(default_factory=list)
    crawl_depth: int = 0
    duration_ms: float = 0.0
    summary: Optional[str] = None
    related_queries: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "total_found": self.total_found,
            "engines_used": [e.value for e in self.engines_used],
            "crawl_depth": self.crawl_depth,
            "duration_ms": round(self.duration_ms, 2),
            "summary": self.summary,
            "related_queries": self.related_queries,
        }




