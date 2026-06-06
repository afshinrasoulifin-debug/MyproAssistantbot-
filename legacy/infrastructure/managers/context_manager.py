
from __future__ import annotations
"""InfraContextManager — AI context lifecycle management."""

import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)



class InfraContextManager:
    """InfraContextManager — AI context lifecycle management."""

    def __init__(self, *, max_items: int = 10000) -> None:
        self._store: Dict[str, Any] = {}
        self._max_items = max_items
        self._access_log: List[Dict] = []
        self._stats = {"gets": 0, "sets": 0, "evictions": 0}
        logger.info("InfraContextManager initialized (max=%d)", max_items)

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a managed item."""
        self._stats["gets"] += 1
        val = self._store.get(key, default)
        self._access_log.append({"op": "get", "key": key, "hit": key in self._store, "at": time.time()})
        return val

    async def set(self, key: str, value: Any, *, ttl: float = 0) -> None:
        """Set a managed item with optional TTL."""
        if len(self._store) >= self._max_items:
            oldest = next(iter(self._store))
            del self._store[oldest]
            self._stats["evictions"] += 1

        self._store[key] = {"value": value, "set_at": time.time(), "ttl": ttl}
        self._stats["sets"] += 1

    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def clear(self) -> int:
        count = len(self._store)
        self._store.clear()
        return count

    async def keys(self, pattern: str = "*") -> List[str]:
        if pattern == "*":
            return list(self._store.keys())
        import fnmatch
        return [k for k in self._store if fnmatch.fnmatch(k, pattern)]

    def size(self) -> int:
        return len(self._store)

    def get_stats(self) -> dict:
        hit_rate = 0
        gets = [a for a in self._access_log if a["op"] == "get"]
        if gets:
            hit_rate = sum(1 for g in gets if g["hit"]) / len(gets) * 100
        return {**self._stats, "size": len(self._store), "hit_rate": round(hit_rate, 1)}


