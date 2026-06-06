
from __future__ import annotations
"""
tg_bot/middlewares/idempotency_middleware.py — Idempotency Guard
v10.2: Ensures each unique request is processed exactly once.

Uses message_id + user_id as idempotency key. Caches results
for a configurable TTL to return cached responses for duplicates.
"""
import hashlib
import logging
import time
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject



logger = logging.getLogger(__name__)


class IdempotencyMiddleware(BaseMiddleware):
    """
    Prevents duplicate processing of the same message.
    
    Unlike DedupMiddleware (which compares text hashes in a short window),
    this tracks message_id to guarantee exactly-once semantics even
    across retries or webhook replays.
    """

    def __init__(
        self,
        dispatcher: Any = None,
        bot: Any = None,
        ttl_seconds: float = 300.0,
        max_cache: int = 50_000,
    ):
        self._dispatcher = dispatcher
        self._bot = bot
        self._ttl = ttl_seconds
        self._max_cache = max_cache
        # key → (timestamp, result)
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._hits = 0
        self._misses = 0

    def _make_key(self, event: TelegramObject) -> Optional[str]:
        """Generate idempotency key from event."""
        msg_id = getattr(event, "message_id", None)
        user = getattr(event, "from_user", None)
        user_id = getattr(user, "id", 0) if user else 0
        chat = getattr(event, "chat", None)
        chat_id = getattr(chat, "id", 0) if chat else 0

        if msg_id is not None:
            raw = f"{chat_id}:{user_id}:{msg_id}"
            return hashlib.md5(raw.encode()).hexdigest()
        return None

    def _cleanup(self) -> None:
        """Evict expired entries."""
        if len(self._cache) <= self._max_cache:
            return
        now = time.time()
        cutoff = now - self._ttl
        self._cache = {
            k: v for k, v in self._cache.items() if v[0] > cutoff
        }

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "cache_size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / max(1, self._hits + self._misses),
        }

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        key = self._make_key(event)

        if key and key in self._cache:
            ts, cached_result = self._cache[key]
            if (time.time() - ts) < self._ttl:
                self._hits += 1
                logger.debug("Idempotency hit: key=%s", key[:8])
                return cached_result

        self._misses += 1
        result = await handler(event, data)

        if key:
            self._cache[key] = (time.time(), result)
            self._cleanup()

        return result


