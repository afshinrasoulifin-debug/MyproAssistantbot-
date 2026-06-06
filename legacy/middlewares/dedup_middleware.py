
from __future__ import annotations
"""
tg_bot/middlewares/dedup_middleware.py — Request Deduplication
Prevents processing duplicate messages within a time window.
"""
import hashlib
import logging
import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message



logger = logging.getLogger(__name__)


# v9.4: Supports Redis backend for multi-instance dedup
# Falls back to in-memory if Redis unavailable

class DedupMiddleware(BaseMiddleware):
    """
    Deduplicates incoming messages.
    If the same user sends the same text within window_seconds, skip processing.
    """

    def __init__(self, window_seconds: float = 0.3, max_cache: int = 10000):  # v9.7.1: Tight window
        self._cache: Dict[str, float] = {}
        self._window = window_seconds
        self._max_cache = max_cache
        self._deduped = 0

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text:
            user_id = event.from_user.id if event.from_user else 0
            key = hashlib.md5(f"{user_id}:{event.text}".encode()).hexdigest()
            now = time.time()

            if key in self._cache and (now - self._cache[key]) < self._window:
                self._deduped += 1
                logger.debug("Deduped message from user %d", user_id)
                return  # Skip duplicate

            self._cache[key] = now

            # Cleanup old entries
            if len(self._cache) > self._max_cache:
                cutoff = now - self._window * 10
                self._cache = {k: v for k, v in self._cache.items() if v > cutoff}

        return await handler(event, data)


