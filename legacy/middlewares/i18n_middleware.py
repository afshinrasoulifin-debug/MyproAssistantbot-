
from __future__ import annotations
"""
tg_bot/middlewares/i18n_middleware.py — Locale Detection v9.4
Auto-detect user language from Telegram settings.
"""
import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

logger = logging.getLogger(__name__)

# Supported languages
SUPPORTED_LOCALES = {"fa", "en", "ar", "tr"}
DEFAULT_LOCALE = "fa"


class I18nMiddleware(BaseMiddleware):
    """Inject user locale into handler data."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        locale = DEFAULT_LOCALE

        # Try to get language from Telegram user
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif hasattr(event, 'from_user') and event.from_user:
            user = event.from_user
        elif hasattr(event, 'message') and hasattr(event.message, 'from_user'):
            user = event.message.from_user if event.message else None

        if user and user.language_code:
            lang = user.language_code[:2].lower()
            if lang in SUPPORTED_LOCALES:
                locale = lang

        data["locale"] = locale
        data["_"] = lambda key, **kw: _translate(key, locale, **kw)

        return await handler(event, data)


def _translate(key: str, locale: str, **kwargs) -> str:
    """Translate a key to the given locale."""
    try:
        from arki_project.utils.i18n import get_i18n
        i18n = get_i18n()
        return i18n.t(key, locale=locale, **kwargs)
    except Exception:
        return key


