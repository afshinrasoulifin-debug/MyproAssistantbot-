
"""executor_pkg.cmd_kill_group — sub-module of executor"""

from __future__ import annotations
from arki_project.exceptions import AgentExecutionError

import io
import os
import signal
from contextlib import redirect_stdout, redirect_stderr
from typing import Any

from aiogram.filters import Command
from aiogram.types import Message, FSInputFile

from arki_project.config import Settings
from arki_project.utils.safe_send import safe_reply, send_long_text

# Sandboxed builtins — no __import__, eval, exec, compile, open, getattr, hasattr, etc.
# v29.0 HARDENED: removed hasattr (probing), kept only pure-computation builtins

__all__ = ['cmd_kill', 'cmd_queue', 'cmd_tasks', 'cmd_tasklog', 'cmd_ws']

async def cmd_kill(message: Message, settings: Settings) -> None:
    """Kill a process by PID."""
    if _deny(message, settings):
        return

    raw = (message.text or "").split(maxsplit=1)
    if len(raw) < 2 or not raw[1].strip().isdigit():
        await safe_reply(message,
            "💀 *Kill Process*\n\n"
            "استفاده: `/kill <PID>`\n\n"
            "مثال: `/kill 12345`"
        )
        return

    pid = int(raw[1].strip())

    # Safety: don't kill self
    if pid == os.getpid():
        await safe_reply(message, "⚠️ نمی‌تونم خودم رو kill کنم!")
        return

    try:
        os.kill(pid, signal.SIGTERM)
        await safe_reply(message, f"✅ SIGTERM → PID `{pid}`")
    except ProcessLookupError:
        await safe_reply(message, f"❌ PID `{pid}` یافت نشد")
    except PermissionError:
        await safe_reply(message, f"❌ دسترسی برای kill PID `{pid}` نیست")
    except AgentExecutionError as exc:
        logger.error("Error in handler: %s", exc)
        await safe_reply(message, f"❌ خطا: `{exc}`")

# ════════════════════════════════════════════════════════
#  /queue — Persistent task queue (persistence + remote exec)
# ════════════════════════════════════════════════════════

@router.message(Command("queue"))
async def cmd_queue(message: Message, settings: Settings) -> None:
    """Queue a persistent task (survives restart)."""
    if _deny(message, settings):
        return

    raw = (message.text or "").split(maxsplit=2)
    if len(raw) < 3:
        await safe_reply(message,
            "📋 *Persistent Task Queue*\n\n"
            "استفاده: `/queue <type> <payload>`\n\n"
            "انواع: `sh`, `exec`, `eval`\n\n"
            "مثال:\n"
            "`/queue sh ls -la /home`\n"
            "`/queue exec print('hello from queue')`\n"
            "`/queue eval 2**100`\n\n"
            "تسک‌ها در دیتابیس ذخیره می‌شن و بعد ریستارت هم اجرا می‌شن."
        )
        return

    task_type = raw[1].strip()
    payload = raw[2].strip()

    if task_type not in ("sh", "exec", "eval"):
        await safe_reply(message, f"❌ نوع نامعتبر: `{task_type}` — فقط `sh`/`exec`/`eval`")
        return

    try:
        submit_task, _, _ = _get_persistent()
        task_id = await submit_task(
            admin_id=message.from_user.id,  # type: ignore[misc]
            chat_id=message.chat.id,
            task_type=task_type,
            payload=payload,
        )
        await safe_reply(message,
            f"📋 *Task #{task_id}* در صف قرار گرفت\n\n"
            f"نوع: `{task_type}`\n"
            f"```\n{payload[:200]}\n```\n"
            "نتیجه بعد از اجرا ارسال می‌شه ✅"
        )
    except AgentExecutionError as exc:
        logger.error("Error in handler: %s", exc)
        await safe_reply(message, f"❌ خطا: `{exc}`")

# ════════════════════════════════════════════════════════
#  /tasks — List persistent tasks
# ════════════════════════════════════════════════════════

@router.message(Command("tasks"))
async def cmd_tasks(message: Message, settings: Settings) -> None:
    """List recent persistent tasks."""
    if _deny(message, settings):
        return

    try:
        _, get_task_list, _ = _get_persistent()
        tasks = await get_task_list()

        if not tasks:
            await safe_reply(message, "📋 صف خالی — هنوز تسکی ثبت نشده")
            return

        status_icons = {
            "pending": "⏳", "running": "🔄",
            "done": "✅", "failed": "❌",
        }

        lines = ["📋 *آخرین تسک‌ها:*\n"]
        for t in tasks:
            icon = status_icons.get(t["status"], "❓")
            elapsed = f"{t['elapsed_ms']}ms" if t["elapsed_ms"] else "-"
            lines.append(
                f"{icon} `#{t['id']}` [{t['type']}] {t['status']} "
                f"| ⏱{elapsed} | `{t['payload']}`"
            )

        await send_long_text(message, "\n".join(lines))
    except AgentExecutionError as exc:
        logger.error("Error in handler: %s", exc)
        await safe_reply(message, f"❌ خطا: `{exc}`")

# ════════════════════════════════════════════════════════
#  /tasklog — View task result
# ════════════════════════════════════════════════════════

@router.message(Command("tasklog"))
async def cmd_tasklog(message: Message, settings: Settings) -> None:
    """View detailed task result."""
    if _deny(message, settings):
        return

    raw = (message.text or "").split(maxsplit=1)
    if len(raw) < 2 or not raw[1].strip().isdigit():
        await safe_reply(message, "📄 استفاده: `/tasklog <task_id>`")
        return

    task_id = int(raw[1].strip())

    try:
        _, _, get_task_detail = _get_persistent()
        task = await get_task_detail(task_id)

        if not task:
            await safe_reply(message, f"❌ تسک `#{task_id}` یافت نشد")
            return

        status_icons = {
            "pending": "⏳", "running": "🔄",
            "done": "✅", "failed": "❌",
        }
        icon = status_icons.get(task["status"], "❓")

        parts = [
            f"{icon} *Task #{task['id']}*\n",
            f"نوع: `{task['type']}`",
            f"وضعیت: `{task['status']}`",
            f"تلاش: `{task['retries']}`",
            f"زمان اجرا: `{task['elapsed_ms']}ms`",
            f"ثبت: `{task['created_at']}`",
        ]

        if task["payload"]:
            parts.append(f"\n📝 *Payload:*\n```\n{task['payload'][:500]}\n```")
        if task["result"]:
            parts.append(f"\n📤 *Result:*\n```\n{task['result'][:1000]}\n```")
        if task["error"]:
            parts.append(f"\n⚠️ *Error:*\n```\n{task['error'][:500]}\n```")

        await send_long_text(message, "\n".join(parts))
    except AgentExecutionError as exc:
        logger.error("Error in handler: %s", exc)
        await safe_reply(message, f"❌ خطا: `{exc}`")

# ════════════════════════════════════════════════════════
#  /ws — WebSocket server status
# ════════════════════════════════════════════════════════

@router.message(Command("ws"))
async def cmd_ws(message: Message, settings: Settings) -> None:
    """Show WebSocket remote server status."""
    if _deny(message, settings):
        return

    try:
        ws_stats = _get_ws()
        stats = ws_stats()

        status = "🟢 فعال" if stats["running"] else "🔴 غیرفعال"
        lines = [
            "🌐 *WebSocket Remote Server*\n",
            f"وضعیت: {status}",
            f"آدرس: `{stats['host']}:{stats['port']}`",
            f"اتصالات: `{stats['connections']}`",
            f"صف: `{stats['queue_size']}`",
        ]

        if stats["connection_details"]:
            lines.append("\n*اتصالات فعال:*")
            for cid, info in stats["connection_details"].items():
                auth = "✅" if info["authenticated"] else "❌"
                lines.append(f"  {auth} `{cid}` — {info['requests']} req")

        await send_long_text(message, "\n".join(lines))
    except AgentExecutionError as exc:
        logger.error("Error in handler: %s", exc)
        await safe_reply(message, f"❌ خطا: `{exc}`")



