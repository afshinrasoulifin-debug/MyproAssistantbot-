
"""
common_pkg/search_submenu.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ── Search Sub-menu ──

@router.callback_query(F.data == "menu:search")
async def cb_search(callback: CallbackQuery) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 جستجوی سریع", callback_data="act:search"),
         InlineKeyboardButton(text="🔬 تحقیق عمیق", callback_data="act:deep")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            "🔍 *جستجو و تحقیق*\n\n"
            "`/search [عبارت]` — جستجوی سریع اینترنت\n"
            "`/deep [موضوع]` — تحقیق عمیق چندزاویه‌ای\n\n"
            "💡 همچنین می‌تونی عادی بنویسی — AI خودش تشخیص میده\n"
            "_Powered by Gemini + Google Search_",
            reply_markup=kb,
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)





