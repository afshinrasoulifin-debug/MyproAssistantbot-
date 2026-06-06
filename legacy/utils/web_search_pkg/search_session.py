
"""
web_search_pkg/search_session.py — SearchSession
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class SearchSession:
    """Track a user's search session for contextual refinement."""

    def __init__(self, user_id: str = "anonymous"):
        self.user_id = user_id
        self._queries: list[str] = []
        self._results_seen: set[str] = set()
        self._created = __import__("time").time()

    def add_query(self, query: str, results: list):
        self._queries.append(query)
        for r in results:
            if hasattr(r, "url"):
                self._results_seen.add(r.url)

    def suggest_refinement(self, query: str) -> str:
        """Suggest a refined query based on session context."""
        if not self._queries:
            return query
        # Add NOT clauses for already-seen content domains
        seen_domains = set()
        for url in self._results_seen:
            try:
                from urllib.parse import urlparse
                d = urlparse(url).netloc
                if d:
                    seen_domains.add(d)
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)
        if seen_domains and len(self._queries) > 2:
            exclusions = " ".join(f"-site:{d}" for d in list(seen_domains)[:3])
            return f"{query} {exclusions}"
        return query

    @property
    def depth(self) -> int:
        return len(self._queries)




