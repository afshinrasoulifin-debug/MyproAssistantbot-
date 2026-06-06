
"""
common_pkg/marketing_titan_submenu.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ── Marketing TITAN Sub-menu ──

@router.callback_query(F.data == "menu:marketing")
async def cb_marketing_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 داشبورد", callback_data="act:marketing_dashboard"),
         InlineKeyboardButton(text="🎯 کمپین", callback_data="act:marketing_campaign")],
        [InlineKeyboardButton(text="🔍 شکارچی B2B", callback_data="act:marketing_hunt"),
         InlineKeyboardButton(text="📧 ارسال پیام", callback_data="act:marketing_outreach")],
        [InlineKeyboardButton(text="🌐 پلتفرم‌ها", callback_data="act:marketing_platforms"),
         InlineKeyboardButton(text="📈 تحلیل بازار", callback_data="act:marketing_analyze")],
        [InlineKeyboardButton(text="🔧 سلامت سیستم", callback_data="act:marketing_health")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            "📢 *Marketing Agent TITAN*\n\n"
            "ایجنت مارکتینگ خودکار با قابلیت‌های حرفه‌ای.\n\n"
            "📋 *دستورات:*\n"
            "`/marketing_dashboard` — داشبورد کامل\n"
            "`/marketing_hunt` — شکار مشتری B2B\n"
            "`/marketing_campaign` — مدیریت کمپین\n"
            "`/marketing_outreach` — عملیات ارسال\n"
            "`/marketing_platforms` — وضعیت پلتفرم‌ها\n"
            "`/marketing_analyze` — تحلیل بازار و رقبا\n"
            "`/marketing_health` — سلامت و زمان‌بندی",
            reply_markup=kb,
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)





