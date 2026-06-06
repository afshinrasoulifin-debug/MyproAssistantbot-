
from __future__ import annotations
"""
tg_bot/utils/distributed_lock.py — Distributed Locking v9.4
Lock user state across instances to prevent race conditions.
Uses Redis if available, falls back to in-memory locks.
"""
import asyncio
import logging
import time
from typing import Dict, Optional, Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class DistributedLock:
    """Async distributed lock with Redis backend or in-memory fallback."""

    def __init__(self, redis_client: Optional[Any]=None) -> None:
        self._redis = redis_client
        self._local_locks: Dict[str, asyncio.Lock] = {}
        self._lock_times: Dict[str, float] = {}

    async def acquire(self, key: str, timeout: float = 10.0, ttl: float = 30.0) -> bool:
        """Acquire lock on a key."""
        if self._redis:
            try:
                lock_key = f"lock:{key}"
                end_time = time.time() + timeout
                while time.time() < end_time:
                    result = await self._redis.set(lock_key, "1", ex=int(ttl), nx=True)
                    if result:
                        return True
                    await asyncio.sleep(0.1)
                return False
            except Exception as e:
                logger.warning("Redis lock failed, using local: %s", e)

        # In-memory fallback
        if key not in self._local_locks:
            self._local_locks[key] = asyncio.Lock()
        try:
            await asyncio.wait_for(self._local_locks[key].acquire(), timeout=timeout)
            self._lock_times[key] = time.time()
            return True
        except asyncio.TimeoutError:
            return False

    async def release(self, key: str) -> Any:
        """Release lock on a key."""
        if self._redis:
            try:
                await self._redis.delete(f"lock:{key}")
                return
            except Exception as _exc:
                logger.debug("Suppressed: %s", _exc)

        if key in self._local_locks and self._local_locks[key].locked():
            self._local_locks[key].release()
        self._lock_times.pop(key, None)

    async def with_lock(self, key: str, coro: Any, timeout: float = 10.0) -> Any:
        """Execute a coroutine under a lock."""
        acquired = await self.acquire(key, timeout)
        if not acquired:
            raise TimeoutError(f"Could not acquire lock: {key}")
        try:
            return await coro
        finally:
            await self.release(key)


_lock: Optional[DistributedLock] = None

def get_distributed_lock() -> DistributedLock:
    global _lock
    if _lock is None:
        _lock = DistributedLock()
    return _lock


