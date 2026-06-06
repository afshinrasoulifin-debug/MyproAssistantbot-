
"""
common_pkg/content_studio_submenu.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ── Content Studio Sub-menu ──

@router.callback_query(F.data == "menu:content_studio")
async def cb_content_studio(callback: CallbackQuery) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 مرکز فرمان", callback_data="act:studio"),
         InlineKeyboardButton(text="🏷 هویت برند", callback_data="act:brand")],
        [InlineKeyboardButton(text="📦 کاتالوگ", callback_data="act:catalog"),
         InlineKeyboardButton(text="🔥 تولید محتوا", callback_data="act:content")],
        [InlineKeyboardButton(text="✍️ کپشن‌ساز", callback_data="act:caption"),
         InlineKeyboardButton(text="🏷 هشتگ‌ساز", callback_data="act:hashtag")],
        [InlineKeyboardButton(text="📅 محتوای هفته", callback_data="act:batch"),
         InlineKeyboardButton(text="🎬 اسکریپت ریلز", callback_data="act:story")],
        [InlineKeyboardButton(text="🧪 تست A/B", callback_data="act:abtest"),
         InlineKeyboardButton(text="📅 تقویم ماهانه", callback_data="act:calendar")],
        [InlineKeyboardButton(text="📝 قالب‌ها", callback_data="act:template"),
         InlineKeyboardButton(text="🎬 ویدیو پلنر", callback_data="act:videoplan")],
        [InlineKeyboardButton(text="📸 UGC کمپین", callback_data="act:ugc"),
         InlineKeyboardButton(text="📦 بسته محتوا", callback_data="act:contentpack")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            "🎬 *استودیوی محتوا — ۱۴ ابزار*\n\n"
            "`/studio` — مرکز فرمان\n"
            "`/brand` — تنظیم هویت برند\n"
            "`/catalog` — کاتالوگ محصولات\n"
            "`/content` — تولید همه‌جانبه\n"
            "`/caption` — کپشن‌ساز (۵ سبک × EN+FI)\n"
            "`/hashtag` — تحقیق هشتگ هوشمند\n"
            "`/batch` — محتوای یک هفته یکجا\n"
            "`/story` — اسکریپت ریلز/استوری\n"
            "`/abtest` — تست A/B کپشن\n"
            "`/calendar` — تقویم محتوای ماهانه\n"
            "`/template` — قالب‌های آماده محتوا\n"
            "🆕 `/videoplan` — ویدیو پلنر AI\n"
            "🆕 `/ugc` — کمپین محتوای کاربرساخت\n"
            "🆕 `/contentpack` — بسته محتوای کامل",
            reply_markup=kb,
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)





