
"""
web_search_pkg/search_result.py — SearchResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class SearchResult:
    """Single search result."""
    title: str
    url: str
    snippet: str
    source: SearchEngine
    rank: int = 0
    relevance_score: float = 0.0
    content_type: ContentType = ContentType.WEBPAGE
    timestamp: Optional[str] = None
    full_content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source.value,
            "rank": self.rank,
            "relevance_score": round(self.relevance_score, 4),
            "content_type": self.content_type.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }




