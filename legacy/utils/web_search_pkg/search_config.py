
"""
web_search_pkg/search_config.py — SearchConfig
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class SearchConfig:
    """Search configuration."""
    max_results: int = 50
    crawl_depth: int = 1
    timeout_seconds: float = 30.0
    engines: List[SearchEngine] = field(default_factory=lambda: [
        SearchEngine.GOOGLE, SearchEngine.BING, SearchEngine.DUCKDUCKGO,
    ])
    content_types: List[ContentType] = field(default_factory=lambda: [
        ContentType.WEBPAGE,
    ])
    language: str = "en"
    region: Optional[str] = None
    safe_search: bool = True
    extract_content: bool = False
    deduplicate: bool = True
    use_cache: bool = True


# ═══════════════════════════════════════════════════════════════════
# URL Normalization
# ═══════════════════════════════════════════════════════════════════



