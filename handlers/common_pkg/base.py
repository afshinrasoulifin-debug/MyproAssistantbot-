
"""
common_pkg/base.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

@router.message(CommandStart())
async def cmd_start(
    message: Message, db_user: User, settings: Settings,
) -> None:
    logger.info(">>> cmd_start TRIGGERED by user %s (chat %s)", 
                message.from_user.id if message.from_user else "?",
                message.chat.id)

    # v9.6: Deep linking — parse /start parameters
    _start_args = (message.text or "").split(maxsplit=1)
    _deep_link_param = _start_args[1] if len(_start_args) > 1 else ""
    if _deep_link_param:
        logger.info("Deep link param: user=%s param=%s",
                     message.from_user.id if message.from_user else "?", _deep_link_param)
        # Handle referral codes: /start ref_XXXXX
        if _deep_link_param.startswith("ref_"):
            _referral_code = _deep_link_param[4:]
            try:
                from arki_project.database.connection import get_session as _get_session
                from sqlalchemy import select as _sel
                from arki_project.database.models import ReferralCode
                async with _get_session() as _rsession:
                    _ref = await _rsession.execute(
                        _sel(ReferralCode).where(ReferralCode.code == _referral_code)
                    )
                    _ref_obj = _ref.scalar_one_or_none()
                    if _ref_obj and _ref_obj.uses < _ref_obj.max_uses:
                        _ref_obj.uses += 1
                        await _rsession.commit()
                        logger.info("Referral %s applied for user %s (uses=%d)",
                                    _referral_code, message.from_user.id, _ref_obj.uses)
            except HandlerError as _ref_err:
                logger.debug("Referral processing: %s", _ref_err)
        # Handle payment callbacks: /start payment_success
        elif _deep_link_param == "payment_success":
            try:
                await message.answer("✅ پرداخت شما با موفقیت ثبت شد! 🎉")
            except HandlerError as _exc:
                logger.debug("Suppressed: %s", _exc)
        elif _deep_link_param == "payment_cancel":
            try:
                await message.answer("❌ پرداخت لغو شد. برای تلاش مجدد: /subscribe")
            except HandlerError as _exc:
                logger.debug("Suppressed: %s", _exc)

    try:
        n_internal = sum(
            1 for m in MODELS.values()
            if (m.provider == "gemini" and settings.ai_api_key)
            or (m.provider == "groq" and settings.groq_api_key)
        )
        n_g0d = sum(1 for m in MODELS.values() if m.provider == "openrouter")
        n = n_internal + n_g0d
        
        # Check APEX status (safe import)
        try:
            from arki_project.extra.router import get_apex_prompt
            uid = message.from_user.id  # type: ignore[union-attr]
            gm_active = get_apex_prompt(uid) is not None
        except HandlerError as exc:
            logger.error("Error in handler: %s", exc)
            gm_active = False
        gm_status = "🟢 فعال" if gm_active else "⚪ غیرفعال"
        
        # Escape user name for Markdown safety
        safe_name = _escape_md(message.from_user.first_name or "کاربر")
        
        greeting = (
            f"🧠 *Arki Engine v{VER} — TITANIUM*\n\n"
            f"سلام {safe_name}! 👋\n\n"
            f"*{n} مدل AI* ({n_internal} داخلی + {n_g0d} APEX) 🚀\n"
            "*+150 دستور • 10 شخصیت • 16 مارکت‌پلیس*\n\n"
            f"🜏 APEX: {gm_status}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 *AI چت* — چت با بهترین مدل‌ها\n"
            "🎨 *استودیو* — تصویر، پوستر، لوگو، بنر\n"
            "🚀 *فروش* — فانل، قیمت‌گذاری، تحلیل رقبا\n"
            "📢 *مارکتینگ* — کمپین، اتوماسیون، B2B\n"
            "🤖 *ایجنت‌ها* — CRM، مالی، مانیتور\n"
            "🧪 *ویکتور* — هوش مصنوعی مستقل\n\n"
            "💬 هر پیامی بفرست → جواب AI\n"
            "📋 از منوی زیر بخش‌ها رو ببین:"
        )
        logger.info(">>> cmd_start sending greeting (len=%d) with main_menu_keyboard", len(greeting))
        result = await safe_reply(message, greeting, reply_markup=main_menu_keyboard())
        logger.info(">>> cmd_start safe_reply returned: %s (msg_id=%s)", 
                    "OK" if result else "NONE",
                    result.message_id if result else "N/A")
        if result is None:
            logger.error("/start handler: safe_reply returned None — message NOT sent to user %s", message.from_user.id)
    except HandlerError as exc:
        logger.error("/start handler CRASHED: %s", exc, exc_info=True)
        # Last resort — try to send a plain text response
        try:
            await message.answer("🧠 Arki Engine v29.0.0 — TITANIUM\n\nسلام! ربات آماده‌ست. یه پیام بفرست.")
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)





