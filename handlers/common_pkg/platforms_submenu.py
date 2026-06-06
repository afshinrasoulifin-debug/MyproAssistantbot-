
"""
common_pkg/platforms_submenu.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ── Platforms Sub-menu ──

@router.callback_query(F.data == "menu:platforms")
async def cb_platforms(callback: CallbackQuery) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 داشبورد پلتفرم‌ها", callback_data="act:platforms"),
         InlineKeyboardButton(text="🔗 اتصال اکانت", callback_data="act:connect")],
        [InlineKeyboardButton(text="📋 انتشار محتوا", callback_data="act:publish"),
         InlineKeyboardButton(text="🏪 مدیریت فروشگاه", callback_data="act:shopmanage")],
        [InlineKeyboardButton(text="🇪🇺 بازار اروپا", callback_data="act:euromarket"),
         InlineKeyboardButton(text="🛒 آگهی مارکت", callback_data="act:listing")],
        [InlineKeyboardButton(text="📊 تحلیل فروشگاه", callback_data="act:analyze"),
         InlineKeyboardButton(text="⭐ مدیریت ریویو", callback_data="act:reviews")],
        [InlineKeyboardButton(text="📦 مدیریت موجودی", callback_data="act:inventory")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            "🌐 *پلتفرم‌ها — 16 مارکت‌پلیس*\n\n"
            "`/platforms` — داشبورد پلتفرم‌ها\n"
            "`/connect` — اتصال اکانت\n"
            "`/publish` — انتشار در همه\n"
            "`/shopmanage` — مدیریت فروشگاه\n"
            "`/euromarket` — راهنمای بازار اروپا\n"
            "`/listing` — آگهی Etsy/Tori.fi\n"
            "`/analyze` — تحلیل فروشگاه\n"
            "🆕 `/reviews` — مدیریت ریویو\n"
            "🆕 `/inventory` — مدیریت موجودی",
            reply_markup=kb,
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)





