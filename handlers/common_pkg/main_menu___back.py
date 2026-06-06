
"""
common_pkg/main_menu___back.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ── Main Menu / Back ──

@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        await safe_edit_text(
            callback.message,
            "🏠 *منوی اصلی*\n\nیک گزینه انتخاب کنید:",
            reply_markup=main_menu_keyboard(),
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)


@router.callback_query(F.data == "menu:back")
async def cb_back_to_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        await safe_edit_text(
            callback.message,
            "🏠 *منوی اصلی*\n\nیک گزینه انتخاب کنید:",
            reply_markup=main_menu_keyboard(),
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)





