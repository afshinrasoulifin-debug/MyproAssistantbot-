
from __future__ import annotations
"""
tg_bot/handlers/template_handler.py — Personal Template Management
"""
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from arki_project.utils.safe_send import safe_reply

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config 
except ImportError:
    pass
logger = logging.getLogger(__name__)
router = Router(name="template")


@router.message(Command("template"))
async def cmd_template(message: Message) -> None:
    """Manage personal content templates."""
    if not message.text or len(message.text.split()) < 2:
        await safe_reply(message,
            "📋 *مدیریت تمپلیت*\n\n"
            "استفاده:\n"
            "• `/template list` — لیست تمپلیت‌ها\n"
            "• `/template add <نام>` — ایجاد تمپلیت\n"
            "• `/template use <نام>` — استفاده از تمپلیت\n"
            "• `/template delete <نام>` — حذف تمپلیت",
            parse_mode="Markdown")
        return

    parts = message.text.split(None, 2)
    action = parts[1].lower()
    name = parts[2] if len(parts) > 2 else ""

    from arki_project.services.content_service import get_content_service
    service = get_content_service()

    if action == "list":
        templates = service.list_templates()
        if not templates:
            await safe_reply(message, "📋 هیچ تمپلیتی ندارید. با `/template add` ایجاد کنید.")
        else:
            text = "📋 *تمپلیت‌های شما:*\n\n"
            for t in templates:
                text += f"• `{t.name}` — {t.content_type}\n"
            await safe_reply(message, text, parse_mode="Markdown")
    elif action == "add" and name:
        await safe_reply(message,
            f"📝 تمپلیت `{name}` آماده ایجاد.\n"
            "متن تمپلیت را در پیام بعدی ارسال کنید.\n"
            f"از {{{{variable}}}} برای متغیرها استفاده کنید.")
    else:
        await safe_reply(message, "❌ دستور نامعتبر.")


