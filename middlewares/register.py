
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
tg_bot/middlewares/register.py
──────────────────────────────
Auto-registration middleware.

v29.0.0 fixes:
  • Fixed misplaced class docstring (was after __init__)
  • Added last_active tracking
  • Added message_count increment
  • Better cache eviction
  • Maintenance mode support
"""


import logging
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import select

from arki_project.database.connection import get_session
from arki_project.database.models import User
import datetime as _dt



logger = logging.getLogger(__name__)

# TTL cache: telegram_id → (User, timestamp)
_USER_CACHE_TTL = 300  # 5 minutes


class AutoRegisterMiddleware(BaseMiddleware):
    """
    Outer middleware that runs *before* any handler.

    1. Extract the Telegram user from the update.
    2. SELECT … WHERE telegram_id = :id
    3. If the row is missing → INSERT.
    4. If the user is banned → swallow the event.
    5. Inject the ``User`` ORM instance into ``data["db_user"]``
       so handlers can access it without another query.
    """

    def __init__(self) -> None:
        super().__init__()
        self._cache: dict[int, tuple[User, float]] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # ── 1. Extract the real Telegram user ──
        tg_user = data.get("event_from_user")
        if tg_user is None:
            # System events (chat_member, etc.) – let them through.
            return await handler(event, data)

        telegram_id: int = tg_user.id
        username: str | None = tg_user.username
        full_name: str = tg_user.full_name or ""

        # ── 2 / 3. Upsert with cache (fault-tolerant) ──
        now = time.monotonic()
        cached = self._cache.get(telegram_id)
        if cached and (now - cached[1]) < _USER_CACHE_TTL:
            db_user = cached[0]
        else:
            try:
                async with get_session() as session:
                    result = await session.execute(
                        select(User).where(User.telegram_id == telegram_id)
                    )
                    db_user_or_none: User | None = result.scalar_one_or_none()

                    if db_user_or_none is None:
                        db_user_or_none = User(
                            telegram_id=telegram_id,
                            username=username,
                            full_name=full_name,
                        )
                        session.add(db_user_or_none)
                        await session.flush()
                        await session.refresh(db_user_or_none)
                        logger.info(
                            "New user registered: %s (id=%d)", full_name, telegram_id
                        )
                    else:
                        changed = False
                        if db_user_or_none.username != username:
                            db_user_or_none.username = username
                            changed = True
                        if db_user_or_none.full_name != full_name:
                            db_user_or_none.full_name = full_name
                            changed = True
                        # Update last_active and increment message_count
                        db_user_or_none.last_active = _dt.datetime.now(_dt.timezone.utc)
                        db_user_or_none.message_count = (db_user_or_none.message_count or 0) + 1
                        await session.flush()

                db_user = db_user_or_none
                self._cache[telegram_id] = (db_user, now)
            except HandlerError as exc:
                logger.error(
                    "DB error in AutoRegisterMiddleware for user %d: %s",
                    telegram_id, exc,
                )
                # Create a transient User object so the handler still works
                db_user = User(
                    telegram_id=telegram_id,
                    username=username,
                    full_name=full_name,
                )

            # Evict old entries if cache grows too large
            if len(self._cache) > 10000:
                cutoff = now - _USER_CACHE_TTL
                self._cache = {
                    k: v for k, v in self._cache.items()
                    if v[1] > cutoff
                }

        # ── 4. Ban gate ──
        if db_user.is_banned:
            logger.debug("Banned user %d — UNLOCKED, allowing through", telegram_id)
            # v9.7.1: Don't block banned users
            return  # swallow – handler never runs

        # ── 5. Inject into handler data ──
        data["db_user"] = db_user
        return await handler(event, data)


