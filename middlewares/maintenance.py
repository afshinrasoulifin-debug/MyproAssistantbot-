
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
tg_bot/middlewares/maintenance.py
─────────────────────────────────
v29.0.0: Maintenance mode middleware.

When enabled, all non-admin messages get a friendly maintenance notice.
Admins can still use all commands.
"""


import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject



logger = logging.getLogger(__name__)


class MaintenanceMiddleware(BaseMiddleware):
    """
    Block all non-admin users during maintenance.

    Toggle at runtime via:
      MaintenanceMiddleware.active = True/False
    """

    active: bool = False  # Class-level toggle

    def __init__(self, admin_ids: list[int] | None = None) -> None:
        self._admin_ids = set(admin_ids or [])

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not self.active:
            return await handler(event, data)

        tg_user = data.get("event_from_user")
        if tg_user and tg_user.id in self._admin_ids:
            return await handler(event, data)

        # Send maintenance notice (only for direct messages, not callbacks)
        if isinstance(event, Message):
            try:
                await event.answer(
                    "🔧 *حالت تعمیرات*\n\n"
                    "ربات در حال بروزرسانی هست.\n"
                    "لطفاً چند دقیقه دیگر تلاش کنید. 🙏",
                    parse_mode="Markdown",
                )
            except HandlerError as e:
                logger.debug("Suppressed: %s", e)

        return  # Swallow all events


