
"""
Cache Layer v9.1
Provides a unified caching interface.
Supports: in-memory (default) and Redis (when available).
"""
import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional
from collections import OrderedDict
from functools import wraps

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class CacheLayer:
    """
    Unified cache with:
    - In-memory LRU (always available)
    - Redis backend (optional, auto-detected)
    - TTL support
    - Cache stats
    """

    def __init__(self, max_size: int = 50000, default_ttl: int = 3600) -> None:
        self._memory: OrderedDict = OrderedDict()
        self._ttls: Dict[str, float] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._redis = None
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "evictions": 0}
        self._try_redis()

    def _try_redis(self) -> Any:
        """Try to connect to Redis if available."""
        try:
            import redis.asyncio as aioredis
            import os
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
            self._redis = aioredis.from_url(
                redis_url,
                decode_responses=True,
                max_connections=50,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )
            logger.info("Redis cache connected: %s", redis_url)
        except Exception:
            logger.warning("Redis not available, falling back to in-memory cache")

    async def get(self, key: str) -> Optional[Any]:
        """Get a cached value."""
        # Check TTL
        if key in self._ttls and time.time() > self._ttls[key]:
            self._memory.pop(key, None)
            del self._ttls[key]
            self._stats["evictions"] += 1

        # Try memory
        if key in self._memory:
            self._memory.move_to_end(key)
            self._stats["hits"] += 1
            return self._memory[key]

        # Try Redis
        if self._redis:
            try:
                val = await self._redis.get(f"arki:{key}")
                if val:
                    result = json.loads(val)
                    self._memory[key] = result  # Populate local cache
                    self._stats["hits"] += 1
                    return result
            except Exception as _exc:
                logger.warning("Redis cache error: %s", _exc)

        self._stats["misses"] += 1
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> Any:
        """Set a cached value with optional TTL."""
        ttl = ttl or self._default_ttl

        # Memory cache
        self._memory[key] = value
        self._ttls[key] = time.time() + ttl
        self._memory.move_to_end(key)
        self._stats["sets"] += 1

        # Evict if too large
        while len(self._memory) > self._max_size:
            evicted_key, _ = self._memory.popitem(last=False)
            self._ttls.pop(evicted_key, None)
            self._stats["evictions"] += 1

        # Redis
        if self._redis:
            try:
                await self._redis.setex(f"arki:{key}", ttl, json.dumps(value, default=str))
            except Exception as _exc:
                logger.warning("Redis cache error: %s", _exc)

    async def delete(self, key: str) -> Any:
        """Delete a cached value."""
        self._memory.pop(key, None)
        self._ttls.pop(key, None)
        if self._redis:
            try:
                await self._redis.delete(f"arki:{key}")
            except Exception as _exc:
                logger.warning("Redis cache error: %s", _exc)

    async def clear(self) -> Any:
        """Clear all cache."""
        self._memory.clear()
        self._ttls.clear()

    def sweep_expired(self) -> int:
        """v29.0: Remove all expired entries in one pass.

        Call periodically (e.g., every 5 minutes) to reclaim memory
        from entries that expired but were never accessed.
        Returns number of entries evicted.
        """
        now = time.time()
        expired_keys = [k for k, exp in self._ttls.items() if now > exp]
        for k in expired_keys:
            self._memory.pop(k, None)
            del self._ttls[k]
            self._stats["evictions"] += 1
        if expired_keys:
            logger.debug("Cache sweep: evicted %d expired entries", len(expired_keys))
        return len(expired_keys)

    def cache_key(self, *args) -> str:
        """Generate a cache key from arguments."""
        raw = json.dumps(args, sort_keys=True, default=str)
        return hashlib.md5(raw.encode()).hexdigest()

    @property
    def stats(self) -> dict:
        total = self._stats["hits"] + self._stats["misses"]
        return {
            **self._stats,
            "size": len(self._memory),
            "hit_rate": f"{self._stats['hits']/total*100:.1f}%" if total else "0%",
            "backend": "redis+memory" if self._redis else "memory",
        }


# Singleton
_cache: Optional[CacheLayer] = None

def get_cache() -> CacheLayer:
    global _cache
    if _cache is None:
        _cache = CacheLayer()
    return _cache


def cached(ttl: int = 3600, prefix: str = "") -> Any:
    """Decorator for caching async function results."""
    def decorator(func: Any) -> Any:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            cache = get_cache()
            key = f"{prefix or func.__name__}:{cache.cache_key(*args, *kwargs.values())}"
            result = await cache.get(key)
            if result is not None:
                return result
            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl=ttl)
            return result
        return wrapper
    return decorator


