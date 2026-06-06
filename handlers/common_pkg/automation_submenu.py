
"""
common_pkg/automation_submenu.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ── Automation Sub-menu ──

@router.callback_query(F.data == "menu:automation")
async def cb_automation(callback: CallbackQuery) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏰ یادآوری", callback_data="act:remind"),
         InlineKeyboardButton(text="📱 QR Code", callback_data="act:qr")],
        [InlineKeyboardButton(text="🔗 کوتاه‌کن URL", callback_data="act:short"),
         InlineKeyboardButton(text="🌤 آب‌و‌هوا", callback_data="act:weather")],
        [InlineKeyboardButton(text="💱 نرخ ارز", callback_data="act:currency"),
         InlineKeyboardButton(text="📰 RSS", callback_data="act:rss")],
        [InlineKeyboardButton(text="📝 یادداشت", callback_data="act:note"),
         InlineKeyboardButton(text="💬 جمله انگیزشی", callback_data="act:quote")],
        [InlineKeyboardButton(text="🔐 رمزساز", callback_data="act:password"),
         InlineKeyboardButton(text="⏰ زمان‌بندی", callback_data="act:schedule")],
        [InlineKeyboardButton(text="📦 موجودی", callback_data="act:inventory"),
         InlineKeyboardButton(text="⭐ ریویو", callback_data="act:reviews")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            "⚡ *اتوماسیون — 12 ابزار*\n\n"
            "⏰ `/remind 30m چای` — یادآوری\n"
            "📱 `/qr [متن/لینک]` — QR Code\n"
            "🔗 `/short [URL]` — کوتاه‌کن\n"
            "🌤 `/weather Helsinki` — آب‌و‌هوا\n"
            "💱 `/currency 100 USD EUR` — تبدیل ارز\n"
            "📰 `/rss [URL]` — خبرخوان\n"
            "📝 `/note [متن]` — یادداشت\n"
            "💬 `/quote` — جمله انگیزشی\n"
            "🔐 `/password [طول]` — رمز ایمن\n"
            "⏰ `/schedule` — زمان‌بندی هوشمند\n"
            "📦 `/inventory` — مدیریت موجودی\n"
            "⭐ `/reviews` — مدیریت ریویو",
            reply_markup=kb,
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)





