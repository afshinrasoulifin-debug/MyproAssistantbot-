
"""
common_pkg/_help.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa

# ──────────────── /help ────────────────

@router.message(Command("help"))
async def cmd_help(message: Message, settings: Settings) -> None:
    n = sum(
        1 for m in MODELS.values()
        if (m.provider == "gemini" and settings.ai_api_key)
        or (m.provider == "groq" and settings.groq_api_key)
    )
    text = (
        f"📖 *Arki Engine v{VER} — راهنمای سریع*\n\n"
        f"🤖 *{n} مدل داخلی:* Gemini + Groq\n"
        "🧬 *59 مدل APEX:* 5 سطح (OpenRouter)\n"
        "🎨 *ساخت عکس:* Flux (رایگان)\n"
        "🗣 *صدا:* TTS 9 صدا + Whisper STT\n\n"
        "━━ *دستورات کلیدی* ━━\n"
        "💬 فقط بنویس → چت AI\n"
        "`/apex` → حالت نامحدود\n"
        "`/race` → مسابقه 59 مدل\n"
        "`/image` → ساخت عکس\n"
        "`/search` → جستجو اینترنت\n"
        "`/deep` → تحقیق عمیق\n"
        "`/voice` → متن به صدا\n"
        "`/victor` → ایجنت ویکتور\n\n"
        "━━ *فروش و محتوا* ━━\n"
        "`/funnel` → فانل فروش\n"
        "`/content` → تولید محتوا\n"
        "`/batch` → محتوای هفته\n"
        "`/poster` → پوستر فروش\n"
        "`/workflow` → پایپلاین خودکار\n\n"
        "━━ *سیستم* ━━\n"
        "`/model` → انتخاب مدل\n"
        "`/persona` → شخصیت AI\n"
        "`/new` → پاک کردن حافظه\n"
        "`/settings` → تنظیمات\n"
        "`/start` → منوی اصلی\n\n"
        "📋 *+150 دستور دیگه* — از منو بخش‌ها رو باز کن"
    )
    await safe_reply(message, text, reply_markup=main_menu_keyboard())


# ═══════════════════════════════════════════════
# MENU CALLBACKS — All properly wired
# ═══════════════════════════════════════════════




