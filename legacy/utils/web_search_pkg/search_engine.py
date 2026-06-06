
"""
web_search_pkg/search_engine.py — SearchEngine
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class SearchEngine(Enum):
    """Supported search engines."""
    GOOGLE = "google"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"
    BRAVE = "brave"
    SEARX = "searx"
    ARXIV = "arxiv"
    SCHOLAR = "scholar"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    PUBMED = "pubmed"
    GITHUB = "github"
    STACKOVERFLOW = "stackoverflow"
    GITLAB = "gitlab"




