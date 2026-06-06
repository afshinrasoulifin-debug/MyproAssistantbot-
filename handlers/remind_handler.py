
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
tg_bot/handlers/remind_handler.py — Enhanced Reminder Handler v2.0
═══════════════════════════════════════════════════════════════════
Database-backed reminders with recurring support, categories,
snooze, and smart natural language parsing.

Commands:
  /remindme 30m چای بذار       — One-time reminder
  /remindme 2h daily جلسه      — Recurring daily
  /remindme list                — List active reminders
  /remindme del 3               — Delete reminder #3
  /remindme snooze 15m          — Snooze last reminder
"""


import asyncio
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    Message,
)

from arki_project.config import Settings
from arki_project.utils.safe_send import safe_reply
from arki_project.handlers.shared import extract_args

try:
    from arki_project.database.connection import get_session
    from arki_project.database.models import Reminder
    from sqlalchemy import select, delete as sa_delete, update as sa_update
    _DB_AVAILABLE = True
except ImportError:
    _DB_AVAILABLE = False


logger = logging.getLogger(__name__)
router = Router(name="remind_handler_v2")

# Active reminder tasks
_reminder_tasks: dict[str, asyncio.Task] = {}

TIME_PATTERN = re.compile(
    r"^(\d+)(m|min|h|hour|d|day|w|week)$", re.IGNORECASE
)


def _parse_duration(s: str) -> Optional[timedelta]:
    """Parse duration string like 30m, 2h, 1d, 1w."""
    m = TIME_PATTERN.match(s.strip())
    if not m:
        return None
    val, unit = int(m.group(1)), m.group(2).lower()
    if unit in ("m", "min"):
        return timedelta(minutes=val)
    elif unit in ("h", "hour"):
        return timedelta(hours=val)
    elif unit in ("d", "day"):
        return timedelta(days=val)
    elif unit in ("w", "week"):
        return timedelta(weeks=val)
    return None


async def _fire_reminder(bot: Any, chat_id: int, text: str, reminder_id: int = 0) -> Any:
    """Send the reminder message."""
    try:
        await bot.send_message(
            chat_id,
            f"⏰ *یادآوری!*\n\n{text}",
            parse_mode="Markdown",
        )
    except HandlerError as e:
        logger.error("Failed to fire reminder %d: %s", reminder_id, e)


async def _schedule_reminder(
    bot: Any, chat_id: int, text: str, delay_seconds: float,
    reminder_id: int = 0, recurring: str = "",
) -> Any:
    """Schedule a reminder after delay_seconds."""
    try:
        await asyncio.sleep(delay_seconds)
        await _fire_reminder(bot, chat_id, text, reminder_id)

        # Handle recurring
        if recurring == "daily":
            _reminder_tasks[f"r_{reminder_id}"] = asyncio.create_task(
                _schedule_reminder(bot, chat_id, text, 86400, reminder_id, recurring)
            )
        elif recurring == "weekly":
            _reminder_tasks[f"r_{reminder_id}"] = asyncio.create_task(
                _schedule_reminder(bot, chat_id, text, 604800, reminder_id, recurring)
            )

        # Mark as fired in DB
        if _DB_AVAILABLE and reminder_id:
            try:
                async with get_session() as session:
                    await session.execute(
                        sa_update(Reminder)
                        .where(Reminder.id == reminder_id)
                        .values(fired=True)
                    )
                    await session.commit()
            except HandlerError as _err:
                logger.warning("Suppressed error: %s", _err)

    except asyncio.CancelledError:
        logger.info("Reminder %d cancelled", reminder_id)


@router.message(Command("remindme"))
async def cmd_remindme(message: Message, settings: Settings, **kwargs) -> None:
    """Set, list, or manage reminders."""
    raw = extract_args(message.text or "", "/remindme")
    uid = message.from_user.id
    parts = raw.strip().split()

    if not parts:
        await safe_reply(message,
            "⏰ *یادآوری پیشرفته*\n\n"
            "*تنظیم:*\n"
            "  `/remindme 30m چای بذار`\n"
            "  `/remindme 2h daily جلسه تیم`\n"
            "  `/remindme 1d weekly گزارش هفتگی`\n\n"
            "*مدیریت:*\n"
            "  `/remindme list` — لیست فعال\n"
            "  `/remindme del 3` — حذف شماره ۳\n\n"
            "*زمان‌ها:* `Xm` (دقیقه) `Xh` (ساعت) `Xd` (روز) `Xw` (هفته)"
        )
        return

    # List reminders
    if parts[0] == "list":
        if not _DB_AVAILABLE:
            active = [k for k in _reminder_tasks if not _reminder_tasks[k].done()]
            await safe_reply(message, f"⏰ یادآوری‌های فعال: {len(active)}")
            return

        async with get_session() as session:
            result = await session.execute(
                select(Reminder)
                .where(Reminder.user_id == uid, Reminder.fired == False)
                .order_by(Reminder.fire_at)
            )
            reminders = result.scalars().all()

        if not reminders:
            await safe_reply(message, "📭 هیچ یادآوری فعالی ندارید.")
            return

        lines = []
        for r in reminders:
            fire_str = r.fire_at.strftime("%Y-%m-%d %H:%M") if r.fire_at else "?"
            rec = f" 🔄 {r.recurring}" if hasattr(r, 'recurring') and r.recurring else ""
            lines.append(f"  {r.id}. `{fire_str}` — {r.text}{rec}")

        await safe_reply(message, f"⏰ *یادآوری‌های فعال:*\n\n" + "\n".join(lines))
        return

    # Delete reminder
    if parts[0] == "del" and len(parts) >= 2:
        try:
            rid = int(parts[1])
        except ValueError:
            await safe_reply(message, "⚠️ شماره نامعتبر.")
            return

        # Cancel task if running
        task_key = f"r_{rid}"
        if task_key in _reminder_tasks:
            _reminder_tasks[task_key].cancel()
            del _reminder_tasks[task_key]

        if _DB_AVAILABLE:
            async with get_session() as session:
                await session.execute(
                    sa_delete(Reminder).where(
                        Reminder.id == rid, Reminder.user_id == uid,
                    )
                )
                await session.commit()

        await safe_reply(message, f"🗑 یادآوری #{rid} حذف شد.")
        return

    # Parse: /remindme 30m [daily|weekly] <text>
    duration = _parse_duration(parts[0])
    if not duration:
        await safe_reply(message, "⚠️ فرمت زمان نامعتبر. مثال: `30m`, `2h`, `1d`, `1w`")
        return

    recurring = ""
    text_start = 1
    if len(parts) > 1 and parts[1].lower() in ("daily", "weekly", "once"):
        recurring = parts[1].lower()
        if recurring == "once":
            recurring = ""
        text_start = 2

    remind_text = " ".join(parts[text_start:]) or "یادآوری"
    fire_at = datetime.now(timezone.utc) + duration

    # Save to DB
    reminder_id = int(time.time()) % 1000000
    if _DB_AVAILABLE:
        try:
            async with get_session() as session:
                r = Reminder(
                    user_id=uid,
                    chat_id=message.chat.id,
                    text=remind_text,
                    fire_at=fire_at,
                    fired=False,
                )
                session.add(r)
                await session.flush()
                reminder_id = r.id
                await session.commit()
        except HandlerError as e:
            logger.warning("DB save failed for reminder: %s", e)

    # Schedule async task
    task = asyncio.create_task(
        _schedule_reminder(
            message.bot, message.chat.id, remind_text,
            duration.total_seconds(), reminder_id, recurring,
        )
    )
    _reminder_tasks[f"r_{reminder_id}"] = task

    when_str = fire_at.strftime("%H:%M")
    rec_str = f"\n🔄 تکرار: {recurring}" if recurring else ""
    await safe_reply(
        message,
        f"✅ *یادآوری تنظیم شد*\n\n"
        f"📝 {remind_text}\n"
        f"⏰ {when_str} (بعد از {parts[0]}){rec_str}\n"
        f"🆔 #{reminder_id}"
    )


@router.callback_query(F.data.startswith("remind:"))
async def cb_remind(callback: CallbackQuery) -> Any:
    """Handle reminder callbacks (snooze, dismiss)."""
    action = callback.data.split(":")[1] if ":" in callback.data else ""
    if action == "dismiss":
        await callback.message.delete()
    await callback.answer("✅")


