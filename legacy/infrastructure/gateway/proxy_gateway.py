
from __future__ import annotations
"""
ProxyGateway — Transparent proxy for API requests with caching and transformation.
"""
import hashlib, logging, time
from typing import Any, Dict

logger = logging.getLogger(__name__)

class ProxyGateway:
    """Proxy AI API calls with caching, retry, and request transformation."""

    def __init__(self, cache_ttl: float = 300.0, max_cache: int = 10000) -> None:
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = cache_ttl
        self._max_cache = max_cache
        self._transforms: list = []
        self._hits = 0
        self._misses = 0

    def _cache_key(self, data: dict) -> str:
        import json
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]

    def add_transform(self, fn: Any) -> None:
        self._transforms.append(fn)

    async def proxy(self, request: dict, handler: Any) -> dict:
        key = self._cache_key(request)
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["time"] < self._cache_ttl:
                self._hits += 1
                return entry["data"]

        # Apply transforms
        for t in self._transforms:
            request = t(request)

        self._misses += 1
        result = await handler(request)

        if len(self._cache) >= self._max_cache:
            oldest = min(self._cache, key=lambda k: self._cache[k]["time"])
            del self._cache[oldest]
        self._cache[key] = {"data": result, "time": time.time()}
        return result

    @property
    def stats(self) -> Any:
        total = self._hits + self._misses
        return {"hits": self._hits, "misses": self._misses,
                "hit_rate": f"{self._hits/max(total,1):.1%}", "cache_size": len(self._cache)}


