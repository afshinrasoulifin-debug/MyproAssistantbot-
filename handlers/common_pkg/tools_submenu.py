
"""
common_pkg/tools_submenu.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ── Tools Sub-menu ──

@router.callback_query(F.data == "menu:tools")
async def cb_tools(callback: CallbackQuery) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 ترجمه", callback_data="act:translate"),
         InlineKeyboardButton(text="📝 خلاصه", callback_data="act:summarize")],
        [InlineKeyboardButton(text="💻 کد", callback_data="act:code"),
         InlineKeyboardButton(text="✏️ ویرایش متن", callback_data="act:polish")],
        [InlineKeyboardButton(text="📖 توضیح", callback_data="act:explain"),
         InlineKeyboardButton(text="🧮 ریاضی", callback_data="act:math")],
        [InlineKeyboardButton(text="💡 طوفان فکری", callback_data="act:brainstorm"),
         InlineKeyboardButton(text="✍️ ساخت فایل", callback_data="act:create")],
        [InlineKeyboardButton(text="🌐 لندینگ‌پیج", callback_data="act:htmlpage"),
         InlineKeyboardButton(text="📤 خروجی CSV", callback_data="act:exportcsv")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            "✨ *ابزارهای متنی — ۱۰ ابزار*\n\n"
            "`/translate [متن]` — ترجمه هوشمند\n"
            "`/summarize [متن]` — خلاصه‌سازی\n"
            "`/code [درخواست]` — نوشتن/اصلاح کد\n"
            "`/polish [متن]` — ویرایش و بهبود نوشته\n"
            "`/explain [موضوع]` — توضیح ساده\n"
            "`/math [مسئله]` — حل ریاضی\n"
            "`/brainstorm [موضوع]` — ایده‌پردازی\n"
            "`/create [نوع] [توضیح]` — ساخت فایل\n"
            "🆕 `/htmlpage [برند] | [نوع]` — لندینگ‌پیج کامل\n"
            "🆕 `/exportcsv [نوع]` — خروجی CSV داده‌ها\n",
            reply_markup=kb,
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)





