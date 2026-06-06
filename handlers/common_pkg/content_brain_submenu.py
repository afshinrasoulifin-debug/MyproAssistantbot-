
"""
common_pkg/content_brain_submenu.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ── Content Brain Sub-menu ──

@router.callback_query(F.data == "menu:content_brain")
async def cb_content_brain(callback: CallbackQuery) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ بهینه‌سازی", callback_data="act:optimize"),
         InlineKeyboardButton(text="📈 ترندها", callback_data="act:trending")],
        [InlineKeyboardButton(text="🤖 محتوای AI", callback_data="act:contentai"),
         InlineKeyboardButton(text="🎨 استایل بصری", callback_data="act:aesthetic")],
        [InlineKeyboardButton(text="📚 سریال محتوا", callback_data="act:series"),
         InlineKeyboardButton(text="✏️ بازنویسی", callback_data="act:rewrite")],
        [InlineKeyboardButton(text="🪝 هوک‌ساز", callback_data="act:hook"),
         InlineKeyboardButton(text="📸 کاروسل", callback_data="act:carousel")],
        [InlineKeyboardButton(text="🎯 CTA", callback_data="act:cta"),
         InlineKeyboardButton(text="📋 آدیت محتوا", callback_data="act:contentaudit")],
        [InlineKeyboardButton(text="📊 بنچمارک رقبا", callback_data="act:benchmark"),
         InlineKeyboardButton(text="⏰ زمان‌بندی", callback_data="act:schedule")],
        [InlineKeyboardButton(text="🔬 A/B تست", callback_data="act:abtest_brain"),
         InlineKeyboardButton(text="📋 آدیت استراتژی", callback_data="act:contentaudit_full")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            "🧠 *هوش محتوا — 14 ابزار*\n\n"
            "`/optimize` — بهینه‌سازی محتوا\n"
            "`/trending` — ترندهای روز\n"
            "`/contentai` — محتوای AI\n"
            "`/aesthetic` — استایل بصری\n"
            "`/series` — سریال محتوا\n"
            "`/rewrite` — بازنویسی\n"
            "`/hook` — هوک‌ساز\n"
            "`/carousel` — کاروسل\n"
            "`/cta` — CTA ساز\n"
            "`/benchmark` — بنچمارک رقبا\n"
            "`/schedule` — زمان‌بندی هوشمند\n"
            "`/contentaudit` — آدیت محتوا\n"
            "🆕 `/abtest` — A/B تست محتوا\n"
            "🆕 `/contentaudit` — آدیت استراتژی",
            reply_markup=kb,
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)





