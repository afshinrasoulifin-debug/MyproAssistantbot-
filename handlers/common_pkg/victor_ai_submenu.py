
"""
common_pkg/victor_ai_submenu.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ── Victor AI Sub-menu ──

@router.callback_query(F.data == "menu:victor")
async def cb_victor_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧪 شروع ویکتور", callback_data="act:victor"),
         InlineKeyboardButton(text="📊 وضعیت مغز", callback_data="act:victorstatus")],
        [InlineKeyboardButton(text="📚 آموزش دادن", callback_data="act:victorteach"),
         InlineKeyboardButton(text="🧠 حافظه ویکتور", callback_data="act:victormemory")],
        [InlineKeyboardButton(text="⚔️ مناظره AI", callback_data="act:debate"),
         InlineKeyboardButton(text="📈 آمار ویکتور", callback_data="act:victorstats")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            "🧪 *ویکتور — هوش مصنوعی مستقل v6.0*\n\n"
            "ویکتور یک AI هست که از صفر شروع می‌کنه و *خودش یاد می‌گیره*.\n"
            "هر چیزی بهش بگی یاد می‌گیره و ازش استفاده می‌کنه.\n\n"
            "📋 *دستورات:*\n"
            "`/victor [سوال]` — سوال از ویکتور\n"
            "`/victor teach [موضوع] [اطلاعات]` — آموزش\n"
            "`/victor forget [موضوع]` — فراموش کردن\n"
            "`/victor memory` — نمایش حافظه\n"
            "`/victor status` — وضعیت مغز\n"
            "`/victor reset` — ریست فکتوری\n"
            "`/victor rules` — قوانین استنتاج\n"
            "`/victor correct [متن]` — اصلاح آخرین جواب\n"
            "`/debate [سوال]` — مناظره AI ها\n"
            "`/victorstats` — آمار عملکرد",
            reply_markup=kb,
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)





