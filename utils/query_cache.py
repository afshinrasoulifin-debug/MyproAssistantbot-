
from __future__ import annotations
"""
tg_bot/utils/query_cache.py — Database Query Cache v9.4
In-memory TTL cache for expensive database queries.
"""
import asyncio
import logging
import time
from typing import Any, Dict, Optional

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class QueryCache:
    """TTL-based query result cache."""

    def __init__(self, default_ttl: float = 60.0, max_size: int = 1000) -> None:
        self._cache: Dict[str, tuple] = {}  # key -> (value, expires_at)
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    async def get_or_fetch(self, key: str, fetch_func: Any, ttl: float = None) -> Any:
        """Get from cache or fetch and cache."""
        if key in self._cache:
            value, expires = self._cache[key]
            if time.time() < expires:
                self._hits += 1
                return value
            del self._cache[key]

        self._misses += 1
        if asyncio.iscoroutinefunction(fetch_func):
            value = await fetch_func()
        else:
            value = fetch_func()

        self._cache[key] = (value, time.time() + (ttl or self._default_ttl))

        # Evict if too large
        if len(self._cache) > self._max_size:
            oldest = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest]

        return value

    def invalidate(self, key: str) -> Any:
        self._cache.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> Any:
        keys = [k for k in self._cache if k.startswith(prefix)]
        for k in keys:
            del self._cache[k]

    def clear(self) -> Any:
        self._cache.clear()

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(1, total) * 100, 1),
        }


_cache: Optional[QueryCache] = None

def get_query_cache() -> QueryCache:
    global _cache
    if _cache is None:
        _cache = QueryCache()
    return _cache


