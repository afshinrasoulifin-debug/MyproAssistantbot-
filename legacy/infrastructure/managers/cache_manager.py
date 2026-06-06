
from __future__ import annotations
"""CacheManager — Multi-tier caching."""
import logging, time
from typing import Any, Dict, Optional



logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, ttl: float = 300.0, max_size: int = 50000) -> None:
        self._cache: Dict[str, dict] = {}
        self._ttl = ttl
        self._max = max_size

    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry and time.time() - entry["time"] < self._ttl:
            return entry["value"]
        return None

    def set(self, key: str, value: Any) -> Any:
        if len(self._cache) >= self._max:
            oldest = min(self._cache, key=lambda k: self._cache[k]["time"])
            del self._cache[oldest]
        self._cache[key] = {"value": value, "time": time.time()}

    def invalidate(self, key: str) -> Any:
        self._cache.pop(key, None)

    def clear(self) -> Any:
        self._cache.clear()


