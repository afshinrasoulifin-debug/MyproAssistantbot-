
"""
common_pkg/sales_engine_submenu.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ── Sales Engine Sub-menu ──

@router.callback_query(F.data == "menu:sales_engine")
async def cb_sales_engine(callback: CallbackQuery) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 فانل فروش", callback_data="act:funnel"),
         InlineKeyboardButton(text="👤 پرسونای مشتری", callback_data="act:buyer")],
        [InlineKeyboardButton(text="♻️ تکثیر محتوا", callback_data="act:repurpose"),
         InlineKeyboardButton(text="🚀 لانچ محصول", callback_data="act:launch")],
        [InlineKeyboardButton(text="🎄 کمپین فصلی", callback_data="act:seasonal"),
         InlineKeyboardButton(text="🔎 تحقیق سئو", callback_data="act:seo")],
        [InlineKeyboardButton(text="📧 ایمیل مارکتینگ", callback_data="act:email"),
         InlineKeyboardButton(text="💰 قیمت‌گذاری", callback_data="act:pricing")],
        [InlineKeyboardButton(text="🔥 فرمول وایرال", callback_data="act:viral"),
         InlineKeyboardButton(text="🤝 اینفلوئنسر", callback_data="act:collab")],
        [InlineKeyboardButton(text="📣 تبلیغ‌ساز", callback_data="act:ads"),
         InlineKeyboardButton(text="⭐ اعتمادسازی", callback_data="act:social")],
        [InlineKeyboardButton(text="📚 Swipe File", callback_data="act:swipe"),
         InlineKeyboardButton(text="🔍 تحلیل رقبا", callback_data="act:competitor")],
        [InlineKeyboardButton(text="📈 پایپلاین", callback_data="act:pipeline"),
         InlineKeyboardButton(text="🎯 امتیازدهی سرنخ", callback_data="act:leadscoring")],
        [InlineKeyboardButton(text="💲 رصد قیمت", callback_data="act:pricewatch"),
         InlineKeyboardButton(text="💎 مگاپست", callback_data="act:megapost")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            "🚀 *موتور فروش — 18 ابزار*\n\n"
            "`/funnel` — فانل فروش کامل\n"
            "`/buyer` — پرسونای مشتری\n"
            "`/launch` — برنامه لانچ محصول\n"
            "`/pricing` — قیمت‌گذاری هوشمند\n"
            "`/competitor` — تحلیل رقبا\n"
            "`/ads` — تبلیغ‌ساز حرفه‌ای\n"
            "`/pipeline` — پایپلاین فروش\n"
            "`/leadscoring` — امتیازدهی سرنخ\n"
            "`/pricewatch` — رصد قیمت رقبا\n\n"
            "📋 هر دکمه رو بزن برای راهنمای کامل",
            reply_markup=kb,
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)





