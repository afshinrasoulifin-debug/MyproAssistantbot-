
from __future__ import annotations
"""
tg_bot/middlewares/poison_pill_middleware.py — Poison Pill Detector
v10.2: Detects and blocks malicious/malformed messages that could crash handlers.

Checks for:
  - Extremely long messages (text bombs)
  - Known exploit patterns (deep nested entities, etc.)
  - Repeated crash-inducing Unicode sequences
"""
import logging
import re
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message



logger = logging.getLogger(__name__)

# Known dangerous patterns
_DANGEROUS_PATTERNS = [
    re.compile(r"(.)\1{500,}"),                       # Char repetition bomb
    re.compile(r"[\u202a-\u202e\u200f\u200e]{50,}"),  # BiDi override flood
    re.compile(r"(?:[\u0300-\u036f]){100,}"),          # Combining char bomb (Zalgo)
]

MAX_TEXT_LENGTH = 50_000  # Telegram max is 4096 but forwarded/edited can be larger
MAX_ENTITIES = 200        # Entity count limit


class PoisonPillMiddleware(BaseMiddleware):
    """
    Blocks messages that match known crash/exploit patterns.
    """

    def __init__(self, bot: Any = None):
        self._bot = bot
        self._blocked = 0
        self._checked = 0

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "checked": self._checked,
            "blocked": self._blocked,
            "block_rate": self._blocked / max(1, self._checked),
        }

    def _is_poisoned(self, event: TelegramObject) -> bool:
        """Check if event contains poison pill patterns."""
        if not isinstance(event, Message):
            return False

        text = event.text or event.caption or ""

        # Length check
        if len(text) > MAX_TEXT_LENGTH:
            logger.warning("Poison pill: text too long (%d chars)", len(text))
            return True

        # Entity count check
        entities = event.entities or []
        if len(entities) > MAX_ENTITIES:
            logger.warning("Poison pill: too many entities (%d)", len(entities))
            return True

        # Pattern checks
        for pattern in _DANGEROUS_PATTERNS:
            if pattern.search(text):
                logger.warning("Poison pill: dangerous pattern detected")
                return True

        return False

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        self._checked += 1

        if self._is_poisoned(event):
            self._blocked += 1
            user_id = getattr(getattr(event, "from_user", None), "id", 0)
            logger.warning(
                "Poison pill blocked from user %d (total blocked: %d)",
                user_id,
                self._blocked,
            )
            return None  # Silently drop

        return await handler(event, data)


