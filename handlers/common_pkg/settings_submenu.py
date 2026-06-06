
"""
common_pkg/settings_submenu.py — Arki Engine v30
Settings submenu + FUNCTIONAL action button handler.
Buttons now EXECUTE commands directly instead of showing help text.
"""
from __future__ import annotations
from ._common import *  # noqa

from arki_project.utils.command_engine import execute_command, needs_input
from arki_project.utils.user_state import set_pending
from arki_project.utils.models_registry import split_for_telegram
from arki_project.exceptions import CallbackError, HandlerError

# ── Settings Sub-menu ──

@router.callback_query(F.data == "menu:settings")
async def cb_settings(callback: CallbackQuery) -> None:
    await callback.answer()

    uid = callback.from_user.id
    try:
        from arki_project.extra.router import get_apex_prompt
        gm = get_apex_prompt(uid) is not None
    except HandlerError:
        gm = False
    gm_icon = "🟢" if gm else "⚪"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 انتخاب مدل", callback_data="act:model"),
         InlineKeyboardButton(text="🎭 شخصیت AI", callback_data="act:persona")],
        [InlineKeyboardButton(text="🎛 AutoTune", callback_data="act:autotune"),
         InlineKeyboardButton(text="📊 تنظیمات فعلی", callback_data="act:settings")],
        [InlineKeyboardButton(text="🔄 پاک کردن حافظه", callback_data="act:new"),
         InlineKeyboardButton(text=f"{gm_icon} APEX", callback_data="extra:apex")],
        [InlineKeyboardButton(text="🔐 GDPR Export", callback_data="act:gdpr_export"),
         InlineKeyboardButton(text="🗑 GDPR Delete", callback_data="act:gdpr_delete")],
        [InlineKeyboardButton(text="💳 اشتراک", callback_data="act:subscribe"),
         InlineKeyboardButton(text="💎 ارتقاء", callback_data="act:upgrade")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            f"⚙️ *تنظیمات*\n\n"
            f"🜏 APEX: {gm_icon} {'فعال' if gm else 'غیرفعال'}\n\n"
            "هر دکمه رو بزن تا مستقیم اجرا بشه! ✅",
            reply_markup=kb,
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)


# ═══════════════════════════════════════════════
# ACTION CALLBACKS — FUNCTIONAL button handler
# ═══════════════════════════════════════════════

@router.callback_query(F.data.startswith("act:"))
async def cb_action_handler(callback: CallbackQuery) -> None:
    """Universal action handler — EXECUTES commands directly."""
    await callback.answer()

    action = callback.data[4:]  # Strip "act:" prefix
    uid = callback.from_user.id
    chat_id = callback.message.chat.id

    # If command needs text input → set pending state and prompt user
    if needs_input(action):
        set_pending(uid, action)

        LABELS = {
            "translate": ("🌐 ترجمه", "متن خود را بفرستید:"),
            "summarize": ("📝 خلاصه", "متن طولانی خود را بفرستید:"),
            "code": ("💻 کد", "درخواست برنامه‌نویسی خود را بنویسید:"),
            "explain": ("📖 توضیح", "موضوع مورد نظر را بنویسید:"),
            "math": ("🧮 ریاضی", "مسئله ریاضی خود را بنویسید:"),
            "brainstorm": ("💡 طوفان فکری", "موضوع را بنویسید:"),
            "polish": ("✏️ ویرایش", "متن خود را بفرستید:"),
            "rewrite": ("✏️ بازنویسی", "متن خود را بفرستید:"),
            "image": ("🎨 تصویر", "توضیح تصویر مورد نظر را بنویسید:"),
            "design": ("🎨 طراحی", "توضیح طرح مورد نظر را بنویسید:"),
            "poster": ("🖼 پوستر", "محصول و قیمت را بنویسید:\nمثال: `شمع ارکی | €24.90`"),
            "search": ("🔍 جستجو", "عبارت جستجو را بنویسید:"),
            "deep": ("🔬 تحقیق عمیق", "موضوع تحقیق را بنویسید:"),
            "brand": ("🏷 هویت برند", "نام و توضیح برند:\nمثال: `Arki Candles | شمع بتنی`"),
            "catalog": ("📦 کاتالوگ", "نام محصول را بنویسید:"),
            "content": ("🔥 تولید محتوا", "محصول و پلتفرم:\nمثال: `شمع ارکی | اینستاگرام`"),
            "caption": ("✍️ کپشن", "نام محصول را بنویسید:"),
            "hashtag": ("🏷 هشتگ", "موضوع را بنویسید:"),
            "batch": ("📅 محتوای هفته", "نام محصول را بنویسید:"),
            "story": ("🎬 ریلز/استوری", "موضوع را بنویسید:"),
            "abtest": ("🧪 تست A/B", "متن فعلی را بنویسید:"),
            "funnel": ("🎯 فانل فروش", "محصول و هدف:\nمثال: `شمع بتنی | فروش آنلاین`"),
            "buyer": ("👤 پرسونا", "نام محصول را بنویسید:"),
            "seo": ("🔎 سئو", "محصول یا نیچ را بنویسید:"),
            "email": ("📧 ایمیل", "محصول و نوع:\nمثال: `شمع | welcome`"),
            "pricing": ("💰 قیمت‌گذاری", "محصول و هزینه تولید را بنویسید:"),
            "viral": ("🔥 وایرال", "نام محصول را بنویسید:"),
            "collab": ("🤝 اینفلوئنسر", "نیچ خود را بنویسید:"),
            "ads": ("📣 تبلیغ", "نام محصول را بنویسید:"),
            "competitor": ("🔍 رقبا", "رقیب و محصول:\nمثال: `Yankee Candle | شمع معطر`"),
            "megapost": ("💎 مگاپست", "موضوع را بنویسید:"),
            "weather": ("🌤 آب‌و‌هوا", "نام شهر را بنویسید:\nمثال: `Helsinki`"),
            "currency": ("💱 ارز", "مبلغ و ارزها:\nمثال: `100 USD EUR`"),
            "workflow": ("🔄 Workflow", "نام محصول را بنویسید:"),
            "voice": ("🗣 متن→صدا", "متن مورد نظر را بنویسید:"),
            "victor": ("🧪 ویکتور", "سوال خود را بنویسید:"),
            "debate": ("⚔️ مناظره", "موضوع مناظره را بنویسید:"),
            "compare": ("⚔️ مقایسه", "سوال خود را بنویسید:"),
            "consensus": ("🏆 اجماع", "سوال خود را بنویسید:"),
            "hook": ("🪝 هوک", "موضوع را بنویسید:"),
            "carousel": ("📸 کاروسل", "موضوع را بنویسید:"),
            "cta": ("🎯 CTA", "نام محصول را بنویسید:"),
            "optimize": ("✨ بهینه‌سازی", "محتوای خود را بفرستید:"),
            "htmlpage": ("🌐 لندینگ‌پیج", "برند و نوع:\nمثال: `شمع ارکی | landing`"),
            "password": ("🔐 رمزساز", "طول رمز را بنویسید (پیش‌فرض 16):"),
            "qr": ("📱 QR", "متن یا لینک را بنویسید:"),
            "note": ("📝 یادداشت", "یادداشت خود را بنویسید:"),
            "remind": ("⏰ یادآوری", "زمان و پیام:\nمثال: `30m چای`"),
        }

        label, prompt = LABELS.get(action, (f"✍️ {action}", "متن مورد نظر را بفرستید:"))

        try:
            await safe_edit_text(
                callback.message,
                f"{label}\n\n{prompt}\n\n_پیام بعدیت پردازش می‌شه..._",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ لغو", callback_data="act:cancel_pending")],
                ]),
            )
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)
        return

    # Command doesn't need input → execute directly
    try:
        result = await execute_command(uid, action)
        chunks = split_for_telegram(result)

        if not chunks:
            await safe_edit_text(
                callback.message,
                "⚠️ پاسخی دریافت نشد.",
                reply_markup=back_to_menu_keyboard(),
            )
            return

        # First chunk → edit the existing message
        try:
            await safe_edit_text(
                callback.message,
                chunks[0],
                reply_markup=back_to_menu_keyboard() if len(chunks) == 1 else None,
            )
        except HandlerError:
            try:
                await callback.message.answer(chunks[0][:4000], parse_mode=None)
            except CallbackError:
                pass

        # Remaining chunks → send as new messages
        for i, chunk in enumerate(chunks[1:], 2):
            rm = back_to_menu_keyboard() if i == len(chunks) else None
            try:
                await callback.message.answer(chunk, parse_mode="Markdown", reply_markup=rm)
            except CallbackError:
                try:
                    await callback.message.answer(chunk[:4000], parse_mode=None, reply_markup=rm)
                except CallbackError:
                    pass

    except HandlerError as e:
        logger.error("Action %s error: %s", action, e)
        try:
            await safe_edit_text(
                callback.message,
                f"❌ خطا: {str(e)[:100]}",
                reply_markup=back_to_menu_keyboard(),
            )
        except HandlerError:
            pass


@router.callback_query(F.data == "act:cancel_pending")
async def cb_cancel_pending(callback: CallbackQuery) -> None:
    """Cancel pending action."""
    from arki_project.utils.user_state import clear_pending
    await callback.answer("لغو شد ✅")
    clear_pending(callback.from_user.id)
    try:
        await safe_edit_text(
            callback.message,
            "✅ لغو شد. می‌تونی از منو دوباره انتخاب کنی.",
            reply_markup=back_to_menu_keyboard(),
        )
    except HandlerError:
        pass


