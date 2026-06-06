
"""
web_search_pkg/search_cache.py — SearchCache
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class SearchCache:
    """LRU cache with TTL for search results."""

    def __init__(self, max_size: int = 1000, ttl_seconds: float = 3600) -> None:
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_order: List[str] = []
        self.hits = 0
        self.misses = 0

    def _cache_key(self, query: str, engine: str,
                   config_hash: str = "") -> str:
        """Generate cache key."""
        raw = f"{query}:{engine}:{config_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, query: str, engine: str = "",
            config_hash: str = "") -> Optional[List[Dict[str, Any]]]:
        """Get cached results if fresh."""
        key = self._cache_key(query, engine, config_hash)
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] <= self.ttl:
                self.hits += 1
                # Move to end (most recent)
                if key in self.access_order:
                    self.access_order.remove(key)
                self.access_order.append(key)
                return entry["results"]
            else:
                del self.cache[key]

        self.misses += 1
        return None

    def put(self, query: str, engine: str, results: List[Dict[str, Any]],
            config_hash: str = "") -> None:
        """Cache search results."""
        key = self._cache_key(query, engine, config_hash)

        # Evict if at capacity
        while len(self.cache) >= self.max_size and self.access_order:
            oldest = self.access_order.pop(0)
            self.cache.pop(oldest, None)

        self.cache[key] = {
            "results": results,
            "timestamp": time.time(),
        }
        self.access_order.append(key)

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / max(1, total), 3),
        }


# ═══════════════════════════════════════════════════════════════════
# Search Engine Core
# ═══════════════════════════════════════════════════════════════════



