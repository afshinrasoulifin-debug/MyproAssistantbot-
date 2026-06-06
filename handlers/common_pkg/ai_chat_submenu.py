
"""
common_pkg/ai_chat_submenu.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ── AI Chat Sub-menu ──

@router.callback_query(F.data == "menu:ai_chat")
async def cb_ai_chat(callback: CallbackQuery) -> None:
    await callback.answer()
    
    # Check APEX for this user
    uid = callback.from_user.id
    try:
        from arki_project.extra.router import get_apex_prompt
        gm = get_apex_prompt(uid) is not None
    except HandlerError:
        gm = False
    gm_text = "\n\n🜏 *APEX فعاله* — پیام‌ها از APEX پردازش می‌شن" if gm else ""
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 انتخاب مدل", callback_data="act:model"),
         InlineKeyboardButton(text="🎭 انتخاب شخصیت", callback_data="act:persona")],
        [InlineKeyboardButton(text="⚔️ مقایسه ۲ مدل", callback_data="act:compare"),
         InlineKeyboardButton(text="🏆 اجماع چند مدل", callback_data="act:consensus")],
        [InlineKeyboardButton(text="🎛 AutoTune", callback_data="act:autotune"),
         InlineKeyboardButton(text="🔄 پاک کردن حافظه", callback_data="act:new")],
        [InlineKeyboardButton(text="🜏 APEX", callback_data="extra:apex"),
         InlineKeyboardButton(text="🟣 Claude Ultra", callback_data="cu:menu")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            "🤖 *چت هوشمند AI*\n\n"
            "💬 هر پیامی بفرست → جواب AI\n\n"
            "📋 *دستورات:*\n"
            "`/model` — انتخاب مدل (19 مدل)\n"
            "`/persona` — شخصیت AI (10 شخصیت)\n"
            "`/compare [سوال]` — مقایسه ۲ مدل\n"
            "`/consensus [سوال]` — اجماع ۳ مدل\n"
            "`/autotune` — تنظیم خودکار پارامترها\n"
            "`/new` — پاک کردن حافظه\n"
            "`/claude_ultra` — چت با Claude (رایگان)\n"
            "`/settings` — مشاهده تنظیمات"
            f"{gm_text}",
            reply_markup=kb,
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)





