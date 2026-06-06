
from __future__ import annotations
"""EdgeNode — Edge computing node for low-latency processing."""
import logging, time
from typing import Any, Dict



logger = logging.getLogger(__name__)


class EdgeNode:
    """Edge node for caching and low-latency responses."""

    def __init__(self, region: str = "local") -> None:
        self.region = region
        self._cache: Dict[str, Any] = {}
        self._hits = 0
        self._misses = 0

    def get_cached(self, key: str) -> Any:
        if key in self._cache:
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def set_cached(self, key: str, value: Any, ttl: float = 300.0) -> None:
        self._cache[key] = {"value": value, "expires": time.time() + ttl}

    def evict_expired(self) -> int:
        now = time.time()
        expired = [k for k, v in self._cache.items()
                   if isinstance(v, dict) and v.get("expires", float("inf")) < now]
        for k in expired:
            del self._cache[k]
        return len(expired)

    def stats(self) -> Dict[str, Any]:
        return {"region": self.region, "cache_size": len(self._cache),
                "hits": self._hits, "misses": self._misses}


