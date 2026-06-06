
"""
web_search_pkg/query_expander.py — QueryExpander
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class QueryExpander:
    """Expand queries for better search coverage."""

    # Common synonyms for query expansion
    SYNONYMS: Dict[str, List[str]] = {
        "error": ["bug", "issue", "problem", "fault"],
        "fix": ["solve", "resolve", "repair", "patch"],
        "fast": ["quick", "rapid", "speedy", "efficient"],
        "slow": ["sluggish", "laggy", "delayed"],
        "security": ["safety", "protection", "defense"],
        "vulnerability": ["weakness", "flaw", "exploit", "CVE"],
        "tutorial": ["guide", "howto", "walkthrough"],
        "example": ["sample", "demo", "illustration"],
        "api": ["endpoint", "interface", "service"],
        "database": ["db", "datastore", "storage"],
    }

    @classmethod
    def expand(cls, query: str, max_expansions: int = 3) -> List[str]:
        """
        Expand a query into multiple variants.

        Strategies:
        1. Synonym replacement
        2. Quoted exact match
        3. Site-specific variants
        """
        queries = [query]

        # Quoted exact match
        queries.append(f'"{query}"')

        # Synonym expansion
        words = query.lower().split()
        for word in words:
            if word in cls.SYNONYMS:
                for syn in cls.SYNONYMS[word][:2]:
                    expanded = query.lower().replace(word, syn)
                    queries.append(expanded)

        return queries[:max_expansions + 1]

    @classmethod
    def to_search_url(cls, query: str, engine: SearchEngine) -> str:
        """Build search URL for a given engine."""
        encoded = urllib.parse.quote(query)

        urls = {
            SearchEngine.GOOGLE: f"https://www.google.com/search?q={encoded}",
            SearchEngine.BING: f"https://www.bing.com/search?q={encoded}",
            SearchEngine.DUCKDUCKGO: f"https://duckduckgo.com/?q={encoded}",
            SearchEngine.BRAVE: f"https://search.brave.com/search?q={encoded}",
            SearchEngine.ARXIV: f"https://arxiv.org/search/?query={encoded}",
            SearchEngine.SCHOLAR: f"https://scholar.google.com/scholar?q={encoded}",
            SearchEngine.GITHUB: f"https://github.com/search?q={encoded}",
            SearchEngine.STACKOVERFLOW: f"https://stackoverflow.com/search?q={encoded}",
        }
        return urls.get(engine, f"https://www.google.com/search?q={encoded}")


# ═══════════════════════════════════════════════════════════════════
# Rate Limiter (Token Bucket)
# ═══════════════════════════════════════════════════════════════════



