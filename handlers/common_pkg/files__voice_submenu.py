
"""
common_pkg/files__voice_submenu.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ── Files & Voice Sub-menu ──

@router.callback_query(F.data == "menu:files_voice")
async def cb_files_voice(callback: CallbackQuery) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 ارسال فایل", callback_data="act:file_info"),
         InlineKeyboardButton(text="🗣 متن ← صدا", callback_data="act:voice")],
        [InlineKeyboardButton(text="🎤 صدا ← متن", callback_data="act:stt"),
         InlineKeyboardButton(text="✍️ ساخت فایل", callback_data="act:create")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            "📄 *فایل و صدا*\n\n"
            "*فایل:*\n"
            "📄 هر فایلی بفرست → پردازش AI\n"
            "  PDF • Excel • Word • CSV • JSON • ZIP • TXT • کد\n"
            "✍️ `/create [توضیح]` — ساخت فایل جدید\n\n"
            "*صدا:*\n"
            "🗣 `/voice [متن]` — متن → صدا (9 صدا)\n"
            "🎤 صدا بفرست → متن (Whisper v3)\n\n"
            "💡 فایل رو با کپشن/سوال بفرست تا تحلیل بشه",
            reply_markup=kb,
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)





