
"""
common_pkg/image_submenu.py — Arki Engine v30.1.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ── Image & Video Sub-menu ──

@router.callback_query(F.data == "menu:image")
async def cb_image(callback: CallbackQuery) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎨 ساخت عکس", callback_data="act:image"),
         InlineKeyboardButton(text="🖼 عکس HD", callback_data="act:hd")],
        [InlineKeyboardButton(text="🎨 طراحی ۳ نسخه", callback_data="act:design"),
         InlineKeyboardButton(text="🎨 ۵ سبک مختلف", callback_data="act:style")],
        [InlineKeyboardButton(text="🎬 ویدیو AI", callback_data="act:video"),
         InlineKeyboardButton(text="🎞 اسلایدشو", callback_data="act:slideshow")],
        [InlineKeyboardButton(text="🎭 انیمیشن", callback_data="act:animate"),
         InlineKeyboardButton(text="🖼 بنر ۶ سایز", callback_data="act:banner")],
        [InlineKeyboardButton(text="🏷 لوگوساز", callback_data="act:logo"),
         InlineKeyboardButton(text="📊 اینفوگرافیک", callback_data="act:infographic")],
        [InlineKeyboardButton(text="📷 مشاور عکاسی", callback_data="act:photoedit"),
         InlineKeyboardButton(text="📸 تحلیل تصویر", callback_data="act:vision")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            "🎨 *تصویر، ویدیو و طراحی — ۱۵ ابزار*\n\n"
            "📸 *عکس:*\n"
            "`/image [توضیح]` — ساخت عکس AI\n"
            "`/hd [توضیح] | [مدل]` — عکس HD (۷ مدل)\n"
            "`/design [توضیح]` — ۳ نسخه طراحی\n"
            "`/style [توضیح]` — ۵ سبک همزمان\n\n"
            "🎬 *ویدیو:*\n"
            "`/video [توضیح]` — تولید ویدیو AI\n"
            "`/slideshow [توضیح]` — اسلایدشو ۶ فریم\n"
            "`/animate [توضیح]` — انیمیشن ۸ فریم\n\n"
            "🛠 *ابزارها:*\n"
            "`/banner [موضوع]` — بنر شبکه اجتماعی (۶ سایز)\n"
            "`/logo [برند]` — لوگوساز AI\n"
            "`/infographic [موضوع]` — اینفوگرافیک AI\n"
            "`/photoedit [محصول]` — مشاور عکاسی\n"
            "📸 عکس بفرست → تحلیل AI Vision\n\n"
            "_Powered by Flux + AI — رایگان و بدون محدودیت_",
            reply_markup=kb,
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)


