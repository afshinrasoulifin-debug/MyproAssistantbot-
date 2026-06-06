
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
tg_bot/middlewares/backpressure_middleware.py — Backpressure Control
v10.2: Limits concurrent request processing to prevent overload.

When active requests exceed max_concurrent, new requests are queued
or rejected with a "server busy" message.
"""
import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message



logger = logging.getLogger(__name__)


class BackpressureMiddleware(BaseMiddleware):
    """
    Controls request flow to prevent overload.
    Tracks concurrent handler executions and applies backpressure
    when the system is under heavy load.
    """

    def __init__(
        self,
        dispatcher: Any = None,
        bot: Any = None,
        max_concurrent: int = 100,
        queue_timeout: float = 30.0,
    ):
        self._dispatcher = dispatcher
        self._bot = bot
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        self._queue_timeout = queue_timeout
        self._active = 0
        self._rejected = 0
        self._total = 0
        self._peak_active = 0

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "active": self._active,
            "peak_active": self._peak_active,
            "total_processed": self._total,
            "rejected": self._rejected,
            "max_concurrent": self._max_concurrent,
        }

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            await asyncio.wait_for(
                self._semaphore.acquire(), timeout=self._queue_timeout
            )
        except asyncio.TimeoutError:
            self._rejected += 1
            user_id = getattr(getattr(event, "from_user", None), "id", 0)
            logger.warning(
                "Backpressure: rejected request from user %d (active=%d)",
                user_id,
                self._active,
            )
            if isinstance(event, Message):
                try:
                    await event.answer(
                        "⏳ سرور شلوغ است، لطفاً چند ثانیه دیگر تلاش کنید."
                    )
                except HandlerError as _e:
                    logger.debug("Could not send busy message: %s", _e)
            return None

        self._active += 1
        self._total += 1
        if self._active > self._peak_active:
            self._peak_active = self._active

        try:
            return await handler(event, data)
        finally:
            self._active -= 1
            self._semaphore.release()


