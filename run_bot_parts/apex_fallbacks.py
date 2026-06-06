
"""
run_bot_parts/apex_fallbacks.py — APEX fallback button handlers
Extracted from run_bot.py to reduce complexity.
"""
from __future__ import annotations
import logging

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from arki_project.utils.safe_send import safe_edit_text

logger = logging.getLogger(__name__)


async def register_apex_fallbacks(dp, bot):
    """Register all APEX fallback button handlers.
    
    These handle callback queries for buttons when the main
    router/submenu system can't load.
    """
    # ── 5. APEX fallback handlers (when extra/router.py can't load) ──
    apex_fallback = Router(name="apex_fallback")

    @apex_fallback.callback_query(F.data == "menu:extra")
    async def fallback_extra_menu(callback: CallbackQuery, **kwargs) -> None:
        await callback.answer()
        from arki_project.keyboards.inline import back_to_menu_keyboard
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🜏 APEX Prompt", callback_data="extra:apex"),
             InlineKeyboardButton(text="🏎 مسابقه مدل‌ها", callback_data="extra:race")],
            [InlineKeyboardButton(text="🧠 Consortium", callback_data="extra:consortium"),
             InlineKeyboardButton(text="💬 Chat پیشرفته", callback_data="extra:chat")],
            [InlineKeyboardButton(text="🐍 Parseltongue", callback_data="extra:parseltongue"),
             InlineKeyboardButton(text="🎛 AutoTune Pro", callback_data="extra:autotunepro")],
            [InlineKeyboardButton(text="🔬 STM", callback_data="extra:stm"),
             InlineKeyboardButton(text="⚡ L1B3RT4S", callback_data="extra:libertas")],
            [InlineKeyboardButton(text="📊 وضعیت APEX", callback_data="extra:status"),
             InlineKeyboardButton(text="ℹ️ Feedback", callback_data="extra:feedback_info")],
            [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
        ])
        await safe_edit_text(
            callback.message,
            "🧬 *APEX Engine*\n\n"
            "موتور پیشرفته AI با قابلیت‌های:\n"
            "• 🜏 APEX System Prompt\n"
            "• 🏎 مسابقه چند مدل همزمان\n"
            "• 🧠 Consortium (اجماع هوش جمعی)\n"
            "• 🐍 Parseltongue (رمزنگاری)\n"
            "• 🎛 AutoTune Pro\n"
            "• 🔬 STM Pipeline\n"
            "• ⚡ L1B3RT4S Combos\n\n"
            "⚠️ _نیاز به اتصال API سرور APEX (پورت 7860)_",
            reply_markup=kb,
        )

    @apex_fallback.callback_query(F.data == "extra:apex")
    async def fallback_apex_toggle(callback: CallbackQuery, **kwargs) -> None:
        """Toggle APEX mode using local bypass data."""
        await callback.answer()
        uid = callback.from_user.id
        from arki_project.utils.apex_bypass import APEX_SYSTEM_PROMPT
        # Simple toggle using in-memory set
        if not hasattr(fallback_apex_toggle, '_users'):
            fallback_apex_toggle._users = set()
        if uid in fallback_apex_toggle._users:
            fallback_apex_toggle._users.discard(uid)
            status = "غیرفعال ⚪"
        else:
            fallback_apex_toggle._users.add(uid)
            status = "فعال 🟢"
        from arki_project.keyboards.inline import back_to_menu_keyboard
        await safe_edit_text(
            callback.message,
            f"🜏 *APEX Mode: {status}*\n\n"
            f"{'پیام‌های شما با APEX System Prompt پردازش می‌شن.' if uid in fallback_apex_toggle._users else 'حالت عادی فعال شد.'}\n\n"
            f"📝 APEX Prompt: {len(APEX_SYSTEM_PROMPT)} کاراکتر",
            reply_markup=back_to_menu_keyboard(),
        )

    @apex_fallback.callback_query(F.data == "apex:toggle")
    async def fallback_apex_toggle2(callback: CallbackQuery, **kwargs) -> None:
        await fallback_apex_toggle(callback, **kwargs)

    @apex_fallback.callback_query(F.data == "extra:status")
    async def fallback_apex_status(callback: CallbackQuery, **kwargs) -> None:
        await callback.answer()
        from arki_project.utils.models_core import MODELS, APEX_TIERS
        from arki_project.keyboards.inline import back_to_menu_keyboard
        tier_info = "\n".join(f"  • {t}: {len(m)} مدل" for t, m in APEX_TIERS.items())
        await safe_edit_text(
            callback.message,
            f"📊 *وضعیت APEX Engine*\n\n"
            f"🤖 مدل‌ها: {len(MODELS)} عدد\n"
            f"📊 تایرها:\n{tier_info}\n\n"
            f"🔌 سرور APEX: ❌ آفلاین\n"
            f"💡 _برای فعال‌سازی کامل، سرور Node.js APEX روی پورت 7860 لازمه_",
            reply_markup=back_to_menu_keyboard(),
        )

    @apex_fallback.callback_query(F.data.startswith("extra:"))
    async def fallback_extra_features(callback: CallbackQuery, **kwargs) -> None:
        """Fallback for all extra: features when APEX server is offline."""
        feature = (callback.data or "").replace("extra:", "")
        await callback.answer()
        FEATURE_INFO = {
            "race": ("🏎 *مسابقه مدل‌ها (Race)*", "چند مدل AI همزمان به سوال شما پاسخ می‌دن و بهترین انتخاب می‌شه.\n\n📋 دستور: `/compare [سوال]`\nیا `/consensus [سوال]`"),
            "consortium": ("🧠 *Consortium*", "هوش جمعی: چند مدل با هم فکر می‌کنن و یک جواب ترکیبی تولید می‌شه.\n\n📋 دستور: `/consensus [سوال]`"),
            "chat": ("💬 *Chat پیشرفته*", "چت با پایپلاین کامل APEX + AutoTune + STM.\n\n📋 فقط پیام بفرست — پایپلاین فعاله!"),
            "parseltongue": ("🐍 *Parseltongue*", "رمزنگاری و تغییر ساختار متن (6 تکنیک، 3 شدت)."),
            "autotunepro": ("🎛 *AutoTune Pro*", "تنظیم خودکار پارامترها بر اساس نوع سوال.\n\n📋 دستور: `/autotune`"),
            "stm": ("🔬 *STM Pipeline*", "ماژول‌های تبدیل معنایی: حذف hedge، مستقیم‌سازی، ساده‌سازی.\n\nدر حال حاضر خودکار فعاله."),
            "libertas": ("⚡ *L1B3RT4S Combos*", "5 ترکیب آزمایش‌شده برای بایپس محدودیت‌ها."),
            "feedback_info": ("ℹ️ *Feedback Loop*", "سیستم بازخورد برای بهبود کیفیت پاسخ‌ها با EMA."),
        }
        title, desc = FEATURE_INFO.get(feature, (f"🔧 *{feature}*", "این قابلیت نیاز به سرور APEX داره."))
        from arki_project.keyboards.inline import back_to_menu_keyboard
        await safe_edit_text(
            callback.message,
            f"{title}\n\n{desc}\n\n⚠️ _برای عملکرد کامل، سرور APEX (پورت 7860) لازمه_",
            reply_markup=back_to_menu_keyboard(),
        )

    @apex_fallback.callback_query(F.data.startswith("sgrp:"))
    async def fallback_sgrp(callback: CallbackQuery, **kwargs) -> None:
        """Model group selection fallback."""
        group = (callback.data or "").replace("sgrp:", "")
        await callback.answer()
        from arki_project.utils.models_core import MODELS
        group_models = {k: v for k, v in MODELS.items() if v.provider == group or group in k}
        model_list = "\n".join(f"  • `{k}` — {v.name}" for k, v in list(group_models.items())[:15])
        from arki_project.keyboards.inline import back_to_menu_keyboard
        await safe_edit_text(
            callback.message,
            f"📦 *مدل‌های {group.title()}*\n\n{model_list or 'مدلی یافت نشد'}\n\n"
            f"📋 برای انتخاب: `/model [نام]`",
            reply_markup=back_to_menu_keyboard(),
        )

    @apex_fallback.callback_query(F.data == "stm:off")
    async def fallback_stm_off(callback: CallbackQuery, **kwargs) -> None:
        await callback.answer("STM غیرفعال شد ✅")
        from arki_project.keyboards.inline import back_to_menu_keyboard
        await safe_edit_text(
            callback.message,
            "🔬 *STM Pipeline*: غیرفعال\n\nبرای فعال‌سازی مجدد از منوی APEX استفاده کنید.",
            reply_markup=back_to_menu_keyboard(),
        )

    @apex_fallback.callback_query(F.data == "plan:trial")
    async def fallback_plan_trial(callback: CallbackQuery, **kwargs) -> None:
        await callback.answer()
        from arki_project.keyboards.inline import back_to_menu_keyboard
        await safe_edit_text(
            callback.message,
            "🎁 *فعال‌سازی آزمایشی*\n\n"
            "✅ شما در حال حاضر دسترسی رایگان به تمام امکانات دارید!\n\n"
            "🤖 136 مدل AI\n"
            "🧠 APEX Engine\n"
            "🔍 جستجوی هوشمند\n"
            "✨ تمام ابزارها",
            reply_markup=back_to_menu_keyboard(),
        )

    # Check if extra router already loaded
    extra_loaded = any(r.name == "extra" for r in dp.sub_routers)
    if not extra_loaded:
        dp.include_router(apex_fallback)
        logger.info("✅ APEX fallback handlers (extra router offline)")
    else:
        logger.info("✅ APEX extra router already loaded — skipping fallbacks")



