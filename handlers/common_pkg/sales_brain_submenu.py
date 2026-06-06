
"""
common_pkg/sales_brain_submenu.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ── Sales Brain Sub-menu ──

@router.callback_query(F.data == "menu:sales_brain")
async def cb_sales_brain(callback: CallbackQuery) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 داشبورد فروش", callback_data="act:dashboard"),
         InlineKeyboardButton(text="👥 مدیریت مشتری", callback_data="act:crm")],
        [InlineKeyboardButton(text="🎯 استراتژی فروش", callback_data="act:salesai"),
         InlineKeyboardButton(text="📦 آپسل", callback_data="act:upsell")],
        [InlineKeyboardButton(text="🎁 باندل", callback_data="act:bundle"),
         InlineKeyboardButton(text="🔄 حفظ مشتری", callback_data="act:retention")],
        [InlineKeyboardButton(text="🔙 بازیابی مشتری", callback_data="act:winback"),
         InlineKeyboardButton(text="👑 وفاداری", callback_data="act:loyalty")],
        [InlineKeyboardButton(text="📊 پیش‌بینی فروش", callback_data="act:forecast"),
         InlineKeyboardButton(text="🛡 مدیریت اعتراض", callback_data="act:objection")],
        [InlineKeyboardButton(text="🎄 راهنمای هدیه", callback_data="act:giftguide"),
         InlineKeyboardButton(text="💎 تحلیل سود", callback_data="act:profit")],
        [InlineKeyboardButton(text="📈 پایپلاین", callback_data="act:pipeline"),
         InlineKeyboardButton(text="🎯 امتیازدهی سرنخ", callback_data="act:leadscoring")],
        [InlineKeyboardButton(text="💲 رصد قیمت", callback_data="act:pricewatch")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            "💰 *هوش فروش — 15 ابزار*\n\n"
            "`/dashboard` — داشبورد کامل فروش\n"
            "`/crm` — مدیریت مشتری (CRM)\n"
            "`/salesai` — استراتژی AI فروش\n"
            "`/upsell` — پیشنهاد آپسل\n"
            "`/bundle` — طراحی باندل\n"
            "`/retention` — حفظ مشتری\n"
            "`/winback` — بازیابی مشتری\n"
            "`/loyalty` — برنامه وفاداری\n"
            "`/forecast` — پیش‌بینی فروش\n"
            "`/objection` — مدیریت اعتراض\n"
            "`/giftguide` — راهنمای هدیه\n"
            "`/profit` — تحلیل سود\n"
            "🆕 `/pipeline` — پایپلاین فروش\n"
            "🆕 `/leadscoring` — امتیازدهی سرنخ\n"
            "🆕 `/pricewatch` — رصد قیمت رقبا",
            reply_markup=kb,
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)





