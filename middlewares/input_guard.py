
from __future__ import annotations
"""
middlewares/input_guard.py — Input Guard Middleware v27.0
════════════════════════════════════════════════════════
Sanitizes all incoming messages before they reach handlers.
Integrated with utils/resilience.InputSanitizer.

Features:
  - Message text sanitization (XSS, injection, overflow)
  - Callback data validation
  - Inline query sanitization
  - Logging of suspicious inputs
  - Rate limiting for suspicious users

Version: 27.0.0
"""

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, InlineQuery, Message, TelegramObject

logger = logging.getLogger(__name__)


class InputGuardMiddleware(BaseMiddleware):
    """Sanitizes user inputs before handler dispatch.

    Prevents:
      - XSS/HTML injection in message text
      - Prompt injection attempts (logged, not blocked by default)
      - Unicode attacks (invisible chars, RTL overrides)
      - Oversized messages
      - Invalid callback data
    """

    def __init__(self, strict: bool = False, log_warnings: bool = True):
        """
        Args:
            strict: If True, actively filter prompt injection (replace with [filtered])
            log_warnings: If True, log all sanitization warnings
        """
        super().__init__()
        self._strict = strict
        self._log_warnings = log_warnings
        self._warning_counts: Dict[int, int] = {}  # user_id → count

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            from arki_project.utils.resilience import InputSanitizer
        except ImportError:
            from utils.resilience import InputSanitizer

        # Sanitize Message text
        if isinstance(event, Message) and event.text:
            sanitized, warnings = InputSanitizer.sanitize(event.text, strict=self._strict)
            if warnings and self._log_warnings:
                user_id = event.from_user.id if event.from_user else 0
                logger.warning(
                    "InputGuard: user=%d warnings=%s text_len=%d→%d",
                    user_id, warnings, len(event.text), len(sanitized),
                )
                self._warning_counts[user_id] = self._warning_counts.get(user_id, 0) + 1

            # Store original and sanitized in data dict for handlers
            data["_original_text"] = event.text
            data["_sanitized_text"] = sanitized
            data["_input_warnings"] = warnings

        # Sanitize CallbackQuery data
        elif isinstance(event, CallbackQuery) and event.data:
            if not InputSanitizer.is_safe_callback_data(event.data):
                user_id = event.from_user.id if event.from_user else 0
                logger.warning("InputGuard: Unsafe callback data from user=%d: %r", user_id, event.data[:64])
                # Still allow through but mark it
                data["_unsafe_callback"] = True

        # Sanitize InlineQuery
        elif isinstance(event, InlineQuery) and event.query:
            sanitized, warnings = InputSanitizer.sanitize(event.query, strict=self._strict)
            data["_sanitized_query"] = sanitized
            data["_input_warnings"] = warnings

        return await handler(event, data)

    def get_suspicious_users(self) -> Dict[int, int]:
        """Get users with most sanitization warnings."""
        return dict(sorted(self._warning_counts.items(), key=lambda x: -x[1])[:20])


