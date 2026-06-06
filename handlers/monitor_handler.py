
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
tg_bot/handlers/monitor_handler.py — Enhanced Web Monitor v2.0
═══════════════════════════════════════════════════════════════
Real web page monitoring with change detection, diff display,
AI-powered change summaries, and scheduled checks.

Commands:
  /watch add <url> [interval_min]  — Add URL to monitor
  /watch list                      — List monitored URLs
  /watch check [id]                — Check now
  /watch del <id>                  — Remove monitor
  /watch diff <id>                 — Show last changes
  /watch ai <id>                   — AI analysis of changes
"""


import asyncio
import hashlib
import logging
import time
from typing import Any

from aiogram import F, Router
from aiogram.enums import ChatAction
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
    from arki_project.database.models import WebMonitor
    from sqlalchemy import select, delete as sa_delete
    _DB_AVAILABLE = True
except ImportError:
    _DB_AVAILABLE = False

try:
    from arki_project.utils.http_session_pool import get_http_pool
    _HTTP_POOL = True
except ImportError:
    _HTTP_POOL = False


logger = logging.getLogger(__name__)
router = Router(name="monitor_handler_v2")

# In-memory monitor state
_monitors: dict[int, dict] = {}  # uid -> {id: {url, last_hash, last_content, last_check, interval}}
_monitor_tasks: dict[str, asyncio.Task] = {}


async def _fetch_page(url: str) -> tuple[str, int]:
    """Fetch a web page and return (content, status_code)."""
    try:
        if _HTTP_POOL:
            pool = get_http_pool()
            session = await pool.get_session("monitor")
            async with session.get(url, timeout=15) as resp:
                content = await resp.text()
                return content, resp.status
        else:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    content = await resp.text()
                    return content, resp.status
    except HandlerError as e:
        logger.error("Fetch failed for %s: %s", url, e)
        return "", 0


def _content_hash(content: str) -> str:
    """Hash page content."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _simple_diff(old: str, new: str, max_lines: int = 10) -> str:
    """Simple line diff between old and new content."""
    old_lines = set(old.splitlines())
    new_lines = new.splitlines()
    added = [l for l in new_lines if l.strip() and l not in old_lines]
    if not added:
        return "تغییری مشخص یافت نشد."
    return "\n".join(f"+ {l[:100]}" for l in added[:max_lines])


async def _check_monitor(bot: Any, uid: int, monitor_id: int, monitor: dict) -> Any:
    """Check a single monitor for changes."""
    url = monitor["url"]
    content, status = await _fetch_page(url)
    if status == 0:
        return

    new_hash = _content_hash(content)
    old_hash = monitor.get("last_hash", "")
    monitor["last_check"] = time.time()

    if old_hash and new_hash != old_hash:
        # Change detected!
        diff = _simple_diff(monitor.get("last_content", ""), content)
        try:
            await bot.send_message(
                uid,
                f"🔔 *تغییر شناسایی شد!*\n\n"
                f"🌐 `{url}`\n\n"
                f"*تغییرات:*\n```\n{diff[:500]}\n```",
                parse_mode="Markdown",
            )
        except HandlerError as e:
            logger.error("Failed to notify user %d: %s", uid, e)

    monitor["last_hash"] = new_hash
    monitor["last_content"] = content[:5000]  # Keep last 5KB


async def _monitor_loop(bot: Any, uid: int, monitor_id: int, monitor: dict) -> Any:
    """Background loop for periodic monitoring."""
    interval = monitor.get("interval", 3600)  # Default 1 hour
    while True:
        try:
            await _check_monitor(bot, uid, monitor_id, monitor)
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except HandlerError as e:
            logger.error("Monitor loop error: %s", e)
            await asyncio.sleep(60)


@router.message(Command("watch"))
async def cmd_watch(message: Message, settings: Settings, **kwargs) -> None:
    """Web monitor management."""
    raw = extract_args(message.text or "", "/watch")
    uid = message.from_user.id
    parts = raw.strip().split()

    if uid not in _monitors:
        _monitors[uid] = {}

    if not parts:
        await safe_reply(message,
            "🕷 *مانیتور وب پیشرفته*\n\n"
            "*دستورات:*\n"
            "  `/watch add https://example.com` — اضافه کردن\n"
            "  `/watch add https://example.com 30` — هر ۳۰ دقیقه\n"
            "  `/watch list` — لیست\n"
            "  `/watch check` — بررسی الان\n"
            "  `/watch check 1` — بررسی شماره ۱\n"
            "  `/watch del 1` — حذف\n"
            "  `/watch diff 1` — نمایش تغییرات"
        )
        return

    action = parts[0].lower()

    if action == "add" and len(parts) >= 2:
        url = parts[1]
        if not url.startswith("http"):
            url = "https://" + url
        interval = int(parts[2]) * 60 if len(parts) > 2 else 3600
        
        mid = len(_monitors[uid]) + 1
        monitor = {
            "url": url, "last_hash": "", "last_content": "",
            "last_check": 0, "interval": interval,
        }
        _monitors[uid][mid] = monitor

        # Save to DB
        if _DB_AVAILABLE:
            try:
                async with get_session() as session:
                    wm = WebMonitor(
                        user_id=uid,
                        url=url,
                        interval_sec=interval,
                        last_hash="",
                    )
                    session.add(wm)
                    await session.commit()
            except HandlerError as e:
                logger.warning("DB save failed: %s", e)

        # Start background monitor
        task = asyncio.create_task(
            _monitor_loop(message.bot, uid, mid, monitor)
        )
        _monitor_tasks[f"{uid}_{mid}"] = task

        intv_str = f"{interval // 60} دقیقه"
        await safe_reply(message,
            f"✅ *مانیتور اضافه شد*\n\n"
            f"🆔 #{mid}\n"
            f"🌐 `{url}`\n"
            f"⏰ هر {intv_str}"
        )
        return

    if action == "list":
        monitors = _monitors.get(uid, {})
        if not monitors:
            await safe_reply(message, "📭 هیچ مانیتوری فعال نیست.")
            return
        lines = []
        for mid, m in monitors.items():
            last = datetime.fromtimestamp(m["last_check"]).strftime("%H:%M") if m["last_check"] else "—"
            changed = "🟢" if m["last_hash"] else "⚪"
            lines.append(f"  {changed} #{mid} `{m['url'][:40]}` — آخرین: {last}")
        await safe_reply(message, f"🕷 *مانیتورها:*\n\n" + "\n".join(lines))
        return

    if action == "check":
        mid = int(parts[1]) if len(parts) > 1 else None
        monitors = _monitors.get(uid, {})
        if mid and mid in monitors:
            await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
            await _check_monitor(message.bot, uid, mid, monitors[mid])
            await safe_reply(message, f"✅ بررسی #{mid} انجام شد.")
        else:
            for m_id, m in monitors.items():
                await _check_monitor(message.bot, uid, m_id, m)
            await safe_reply(message, f"✅ بررسی {len(monitors)} مانیتور انجام شد.")
        return

    if action == "del" and len(parts) >= 2:
        try:
            mid = int(parts[1])
        except ValueError:
            await safe_reply(message, "⚠️ شماره نامعتبر.")
            return
        monitors = _monitors.get(uid, {})
        if mid in monitors:
            del monitors[mid]
            task_key = f"{uid}_{mid}"
            if task_key in _monitor_tasks:
                _monitor_tasks[task_key].cancel()
                del _monitor_tasks[task_key]
            await safe_reply(message, f"🗑 مانیتور #{mid} حذف شد.")
        else:
            await safe_reply(message, f"⚠️ مانیتور #{mid} یافت نشد.")
        return

    if action == "diff" and len(parts) >= 2:
        try:
            mid = int(parts[1])
        except ValueError:
            await safe_reply(message, "⚠️ شماره نامعتبر.")
            return
        monitors = _monitors.get(uid, {})
        m = monitors.get(mid)
        if not m or not m.get("last_content"):
            await safe_reply(message, "⚠️ هنوز محتوایی ذخیره نشده.")
            return
        content_preview = m["last_content"][:1000]
        await safe_reply(message,
            f"📄 *آخرین محتوای #{mid}:*\n\n```\n{content_preview}\n```"
        )
        return

    await safe_reply(message, "⚠️ دستور نامعتبر. `/watch` را ببینید.")


@router.callback_query(F.data.startswith("watch:"))
async def cb_watch(callback: CallbackQuery) -> Any:
    """Handle monitor callbacks."""
    await callback.answer("✅")


