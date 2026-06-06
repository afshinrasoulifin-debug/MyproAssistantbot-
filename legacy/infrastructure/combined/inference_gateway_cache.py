
from __future__ import annotations
"""
InferenceGatewayCache — Combines inference engine + gateway + caching.
"""
import hashlib, logging, time
from typing import Any, Dict, Optional



logger = logging.getLogger(__name__)

class InferenceGatewayCache:
    """Inference gateway with built-in intelligent caching."""

    def __init__(self, cache_ttl: float = 600.0, max_cache: int = 50000) -> None:
        self._cache: Dict[str, Dict] = {}
        self._ttl = cache_ttl
        self._max = max_cache
        self._hits = 0
        self._misses = 0

    def _key(self, data: Any) -> str:
        return hashlib.sha256(str(data).encode()).hexdigest()[:16]

    async def infer(self, request: dict, handler: Optional[Any]=None) -> dict:
        key = self._key(request)
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["time"] < self._ttl:
                self._hits += 1
                return entry["result"]

        self._misses += 1
        result = await handler(request) if handler else request

        if len(self._cache) >= self._max:
            oldest = min(self._cache, key=lambda k: self._cache[k]["time"])
            del self._cache[oldest]
        self._cache[key] = {"result": result, "time": time.time()}
        return result


