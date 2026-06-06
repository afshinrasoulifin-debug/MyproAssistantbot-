
"""
common_pkg/product_auto_submenu.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ── Product Auto Sub-menu ──

@router.callback_query(F.data == "menu:product_auto")
async def cb_product_auto(callback: CallbackQuery) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 افزودن محصول", callback_data="act:addproduct"),
         InlineKeyboardButton(text="📋 لیست محصولات", callback_data="act:products")],
        [InlineKeyboardButton(text="✏️ ویرایش", callback_data="act:editproduct"),
         InlineKeyboardButton(text="🗑 حذف", callback_data="act:delproduct")],
        [InlineKeyboardButton(text="🔄 پایپلاین خودکار", callback_data="act:autopipeline"),
         InlineKeyboardButton(text="📌 صف انتشار", callback_data="act:queue")],
        [InlineKeyboardButton(text="📊 فروش", callback_data="act:sales"),
         InlineKeyboardButton(text="📊 داشبورد", callback_data="act:dashboard")],
        [InlineKeyboardButton(text="📅 وظایف هفتگی", callback_data="act:weeklytasks"),
         InlineKeyboardButton(text="📝 قالب‌ها", callback_data="act:templates")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            "📦 *اتوماسیون محصول — 11 ابزار*\n\n"
            "مدیریت کامل محصولات از A تا Z",
            reply_markup=kb,
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)





