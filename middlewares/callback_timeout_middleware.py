
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
tg_bot/middlewares/callback_timeout_middleware.py — Callback Timeout v9.4
Auto-answer callback queries to avoid Telegram's 60-second timeout error.
"""
import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject



logger = logging.getLogger(__name__)


class CallbackTimeoutMiddleware(BaseMiddleware):
    """Auto-answer callback queries if handler is too slow."""

    def __init__(self, timeout: float = 25.0):
        self._timeout = timeout

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        answered = False

        async def auto_answer():
            nonlocal answered
            await asyncio.sleep(self._timeout)
            if not answered:
                try:
                    await event.answer("⏳ در حال پردازش...")
                    answered = True
                except HandlerError as _exc:
                    logger.debug("Suppressed: %s", _exc)

        timer = asyncio.create_task(auto_answer())
        try:
            result = await handler(event, data)
            answered = True
            return result
        finally:
            timer.cancel()


