
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
Handler Utilities — Common patterns extracted from handlers.

Reduces code duplication across handlers and ensures consistent behavior.
"""

import asyncio
import functools
import logging
import time
from typing import Optional, Callable, Any

from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────
# 1. Admin-only decorator
# ─────────────────────────────────────────────────────

def admin_only(func: Callable) -> Callable:
    """Only allow admin users."""
    @functools.wraps(func)
    async def wrapper(message: Message, *args, **kwargs) -> Any:
        settings = kwargs.get("settings")
        if settings and message.from_user:
            if message.from_user.id not in settings.admin_ids:
                await message.answer("⛔ فقط ادمین‌ها دسترسی دارند.")
                return
        return await func(message, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────
# 2. Rate limit decorator
# ─────────────────────────────────────────────────────

_user_last_call: dict[int, float] = {}

def rate_limit(seconds: float = 2.0) -> Any:
    """Per-user rate limit decorator."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(message: Message, *args, **kwargs) -> Any:
            uid = message.from_user.id if message.from_user else 0
            now = time.time()
            last = _user_last_call.get(uid, 0)
            if now - last < seconds:
                remaining = seconds - (now - last)
                await message.answer(f"⏳ لطفاً {remaining:.0f} ثانیه صبر کنید...")
                return
            _user_last_call[uid] = now
            return await func(message, *args, **kwargs)
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────
# 3. Typing indicator
# ─────────────────────────────────────────────────────

def with_typing(func: Callable) -> Callable:
    """Show 'typing...' while handler runs."""
    @functools.wraps(func)
    async def wrapper(message: Message, *args, **kwargs) -> Any:
        async def keep_typing() -> Any:
            try:
                while True:
                    await message.answer_chat_action("typing")
                    await asyncio.sleep(4)
            except asyncio.CancelledError:
                pass

        typing_task = asyncio.create_task(keep_typing())
        try:
            return await func(message, *args, **kwargs)
        finally:
            typing_task.cancel()
            try:
                await typing_task
            except asyncio.CancelledError:
                pass
    return wrapper


# ─────────────────────────────────────────────────────
# 4. Error boundary
# ─────────────────────────────────────────────────────

def safe_handler(user_message: str = "⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.") -> Any:
    """Catch-all error handler decorator."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except HandlerError as e:
                logger.error("Handler %s failed: %s", func.__name__, e, exc_info=True)
                for arg in args:
                    if isinstance(arg, Message):
                        try:
                            await arg.answer(user_message)
                        except HandlerError as _err:
                            logger.warning("Suppressed error: %s", _err)
                        break
                    elif isinstance(arg, CallbackQuery):
                        try:
                            await arg.answer(user_message, show_alert=True)
                        except HandlerError as _err:
                            logger.warning("Suppressed error: %s", _err)
                        break
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────
# 5. Pagination helper
# ─────────────────────────────────────────────────────

def paginate(items: list, page: int = 1, per_page: int = 10) -> dict:
    """Paginate a list of items."""
    total = len(items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page

    return {
        "items": items[start:end],
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


# ─────────────────────────────────────────────────────
# 6. Message formatter
# ─────────────────────────────────────────────────────

def format_table(headers: list[str], rows: list[list[str]], align: str = "right") -> str:
    """Format a simple table for Telegram (monospace)."""
    if not rows:
        return "خالی"

    all_rows = [headers] + rows
    widths = [max(len(str(row[i])) for row in all_rows) for i in range(len(headers))]

    def fmt_row(row: Any) -> Any:
        cells = []
        for i, cell in enumerate(row):
            s = str(cell)
            cells.append(s.rjust(widths[i]) if align == "right" else s.ljust(widths[i]))
        return " │ ".join(cells)

    lines = [fmt_row(headers)]
    lines.append("─" * (sum(widths) + 3 * (len(widths) - 1)))
    for row in rows:
        lines.append(fmt_row(row))

    return "\n".join(lines)


# ─────────────────────────────────────────────────────
# 7. Input validation
# ─────────────────────────────────────────────────────

def validate_command_args(message: Message, min_args: int = 1,
                          usage: str = "") -> Optional[list[str]]:
    """Validate command arguments. Returns args list if valid, None if invalid."""
    text = message.text or ""
    parts = text.split(maxsplit=min_args)
    args = parts[1:] if len(parts) > 1 else []

    if len(args) < min_args:
        return None

    return args


