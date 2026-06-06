
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
tg_bot/middlewares/plan_enforcement_middleware.py — Plan Enforcement v29.0.0
Checks user's daily token budget before processing AI requests.
"""
import logging
from typing import Any, Awaitable, Callable, Dict, Set
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

logger = logging.getLogger(__name__)

# Plan limits (tokens per day). Set to high values for generous defaults.
PLAN_LIMITS = {
    "free": 50_000,
    "trial": 200_000,
    "pro": 1_000_000,
    "business": 5_000_000,
    "enterprise": 999_999_999,
}

EXEMPT_COMMANDS = {"/start", "/help", "/subscribe", "/billing", "/settings"}


class PlanEnforcementMiddleware(BaseMiddleware):
    """Check token budget before processing message."""

    def __init__(self, admin_ids: set | list = ()):
        self._admin_ids: Set[int] = set(admin_ids) if admin_ids else set()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Always allow admins
        user = getattr(event, "from_user", None)
        if user and user.id in self._admin_ids:
            return await handler(event, data)

        # Always allow exempt commands
        if isinstance(event, Message) and event.text:
            cmd = event.text.split()[0] if event.text.startswith("/") else ""
            if cmd in EXEMPT_COMMANDS:
                return await handler(event, data)

        # Check token budget
        if user:
            try:
                from arki_project.utils.token_tracker import check_token_budget
                allowed, used, budget = await check_token_budget(user.id)
                if not allowed:
                    if isinstance(event, Message):
                        await event.answer(
                            "⚠️ سقف توکن روزانه شما تمام شده.\n"
                            f"مصرف: {used:,} / {budget:,}\n"
                            "فردا ریست می‌شود یا پلن خود را ارتقا دهید: /subscribe"
                        )
                    return None
            except HandlerError as e:
                logger.debug("Plan check error (allowing): %s", e)

        return await handler(event, data)


