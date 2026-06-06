
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
from typing import Any
tg_bot/handlers/collab_handler.py — Collaboration Workspace v2.0
═══════════════════════════════════════════════════════════════
Team collaboration tools: shared notes, task boards,
project tracking, and team AI discussions.

Commands:
  /collab create <name>       — Create workspace
  /collab list                — List workspaces
  /collab note <text>         — Add note to active workspace
  /collab task <text>         — Add task
  /collab tasks               — List tasks
  /collab done <id>           — Mark task done
  /collab share <user_id>     — Share workspace
  /collab brainstorm <topic>  — Team brainstorm with AI
"""


import logging
import time

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    Message,
)

from arki_project.config import Settings
from arki_project.utils.ai_client import AIClient
from arki_project.utils.safe_send import safe_reply
from arki_project.handlers.shared import extract_args


logger = logging.getLogger(__name__)
router = Router(name="collab_handler_v2")

# In-memory workspace storage
_workspaces: dict[str, dict] = {}  # ws_id -> {name, owner, members, notes, tasks}
_user_active_ws: dict[int, str] = {}  # uid -> active workspace id


def _get_ws(uid: int) -> dict | None:
    """Get user's active workspace."""
    ws_id = _user_active_ws.get(uid)
    if ws_id and ws_id in _workspaces:
        return _workspaces[ws_id]
    return None


def _ws_id(uid: int, name: str) -> str:
    return f"{uid}_{name.replace(' ', '_').lower()}"


@router.message(Command("collab"))
async def cmd_collab(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """Collaboration workspace manager."""
    raw = extract_args(message.text or "", "/collab")
    uid = message.from_user.id
    parts = raw.strip().split(maxsplit=1)

    if not parts:
        ws = _get_ws(uid)
        ws_name = ws["name"] if ws else "—"
        await safe_reply(message,
            "👥 *فضای همکاری*\n\n"
            f"📂 فعال: *{ws_name}*\n\n"
            "*دستورات:*\n"
            "  `/collab create نام` — ایجاد فضا\n"
            "  `/collab list` — لیست فضاها\n"
            "  `/collab note متن` — افزودن یادداشت\n"
            "  `/collab task متن` — افزودن تسک\n"
            "  `/collab tasks` — لیست تسک‌ها\n"
            "  `/collab done 1` — تکمیل تسک\n"
            "  `/collab brainstorm موضوع` — طوفان فکری AI\n"
            "  `/collab report` — گزارش پروژه"
        )
        return

    action = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    # Create workspace
    if action == "create" and args:
        wid = _ws_id(uid, args)
        _workspaces[wid] = {
            "name": args,
            "owner": uid,
            "members": {uid},
            "notes": [],
            "tasks": [],
            "created": time.time(),
        }
        _user_active_ws[uid] = wid
        await safe_reply(message, f"✅ فضای *{args}* ایجاد شد و فعال است.")
        return

    # List workspaces
    if action == "list":
        user_ws = [
            (wid, ws) for wid, ws in _workspaces.items()
            if uid in ws["members"]
        ]
        if not user_ws:
            await safe_reply(message, "📭 فضایی ندارید. `/collab create نام`")
            return
        lines = []
        for wid, ws in user_ws:
            active = "👉 " if _user_active_ws.get(uid) == wid else "  "
            lines.append(
                f"{active}*{ws['name']}* — {len(ws['notes'])} یادداشت, {len(ws['tasks'])} تسک"
            )
        await safe_reply(message, "📂 *فضاهای شما:*\n\n" + "\n".join(lines))
        return

    # Switch workspace
    if action == "switch" and args:
        wid = _ws_id(uid, args)
        if wid in _workspaces:
            _user_active_ws[uid] = wid
            await safe_reply(message, f"✅ فضای *{args}* فعال شد.")
        else:
            await safe_reply(message, f"⚠️ فضای `{args}` یافت نشد.")
        return

    # Add note
    if action == "note" and args:
        ws = _get_ws(uid)
        if not ws:
            await safe_reply(message, "⚠️ ابتدا فضایی ایجاد کنید: `/collab create نام`")
            return
        ws["notes"].append({
            "text": args, "author": uid, "ts": time.time(),
        })
        await safe_reply(message, f"📝 یادداشت اضافه شد. (مجموع: {len(ws['notes'])})")
        return

    # Add task
    if action == "task" and args:
        ws = _get_ws(uid)
        if not ws:
            await safe_reply(message, "⚠️ ابتدا فضا ایجاد کنید.")
            return
        task_id = len(ws["tasks"]) + 1
        ws["tasks"].append({
            "id": task_id, "text": args, "done": False,
            "author": uid, "ts": time.time(),
        })
        await safe_reply(message, f"✅ تسک #{task_id} اضافه شد: *{args}*")
        return

    # List tasks
    if action == "tasks":
        ws = _get_ws(uid)
        if not ws:
            await safe_reply(message, "⚠️ فضایی فعال نیست.")
            return
        tasks = ws["tasks"]
        if not tasks:
            await safe_reply(message, "📭 تسکی وجود ندارد.")
            return
        lines = []
        for t in tasks:
            icon = "✅" if t["done"] else "⬜"
            lines.append(f"  {icon} #{t['id']} {t['text']}")
        done_count = sum(1 for t in tasks if t["done"])
        await safe_reply(message,
            f"📋 *تسک‌های {ws['name']}:* ({done_count}/{len(tasks)} تکمیل)\n\n"
            + "\n".join(lines)
        )
        return

    # Mark done
    if action == "done" and args:
        ws = _get_ws(uid)
        if not ws:
            await safe_reply(message, "⚠️ فضایی فعال نیست.")
            return
        try:
            tid = int(args)
        except ValueError:
            await safe_reply(message, "⚠️ شماره نامعتبر.")
            return
        for t in ws["tasks"]:
            if t["id"] == tid:
                t["done"] = True
                await safe_reply(message, f"✅ تسک #{tid} تکمیل شد!")
                return
        await safe_reply(message, f"⚠️ تسک #{tid} یافت نشد.")
        return

    # AI Brainstorm
    if action == "brainstorm" and args:
        ws = _get_ws(uid)
        ws_context = ""
        if ws:
            notes = "\n".join(n["text"] for n in ws["notes"][-5:])
            tasks = "\n".join(t["text"] for t in ws["tasks"][-5:])
            ws_context = f"\nProject notes:\n{notes}\nTasks:\n{tasks}" if notes or tasks else ""

        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        prompt = (
            f"Brainstorm creative ideas about: {args}\n"
            f"{ws_context}\n\n"
            "Generate 5-7 creative, actionable ideas. In Farsi. Use emojis."
        )
        try:
            result = await ai_client.ask(
                user_id=uid,
                text=prompt,
                system_prompt="You are a creative strategist. Generate innovative, practical ideas.",
                temperature=0.9,
            )
            await safe_reply(message, f"💡 *طوفان فکری — {args}:*\n\n{result}")
        except HandlerError as e:
            logger.error("brainstorm error: %s", e)
            await safe_reply(message, "⚠️ خطا در طوفان فکری.")
        return

    # Report
    if action == "report":
        ws = _get_ws(uid)
        if not ws:
            await safe_reply(message, "⚠️ فضایی فعال نیست.")
            return
        total_tasks = len(ws["tasks"])
        done_tasks = sum(1 for t in ws["tasks"] if t["done"])
        total_notes = len(ws["notes"])
        members = len(ws["members"])
        pct = (done_tasks * 100 // total_tasks) if total_tasks else 0
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)

        await safe_reply(message,
            f"📊 *گزارش: {ws['name']}*\n\n"
            f"👥 اعضا: {members}\n"
            f"📝 یادداشت‌ها: {total_notes}\n"
            f"📋 تسک‌ها: {done_tasks}/{total_tasks}\n"
            f"📈 پیشرفت: [{bar}] {pct}%"
        )
        return

    await safe_reply(message, "⚠️ دستور نامعتبر. `/collab` را ببینید.")


@router.callback_query(F.data.startswith("collab:"))
async def cb_collab(callback: CallbackQuery) -> Any:
    """Handle collab callbacks."""
    await callback.answer("✅")


