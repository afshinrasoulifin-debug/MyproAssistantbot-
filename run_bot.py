
"""
Arki Engine v30 — TITANIUM — Bot Runner
========================================
Entry point for the Telegram bot. Handles:
  - Bot lifecycle (startup, shutdown, polling)
  - Router registration (18 submenus + commands + AI chat)
  - APEX fallback handlers (when extra/router.py is offline)
  - Catch-all AI text handler via g4f free providers
  - Error handling and graceful degradation
"""
import asyncio
import logging
import os
import sys
import time
from arki_project.exceptions import ArkiBaseError

os.environ.setdefault("BOT_TOKEN", "8973741555:AAEnTYLlCerm-4xNFfGBIAexmCyHtNxi98A")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///data/arki.db")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("TZ", "Asia/Tehran")

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, ErrorEvent,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatAction

from arki_project.config import load_settings
from arki_project.keyboards.inline import main_menu_keyboard
from arki_project.utils.safe_send import safe_reply, safe_edit_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("arki.bot")


def _escape_md(text: str) -> str:
    for ch in ("*", "_", "`", "[", "]"):
        text = text.replace(ch, f"\\{ch}")
    return text


async def main():
    settings = load_settings()
    logger.info("🧠 Arki Engine v30 — TITANIUM")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()
    dp["settings"] = settings

    # ── Database ──
    try:
        from arki_project.database.connection import init_db
        await init_db(settings.database_url)
        logger.info("✅ Database initialized")
    except ArkiBaseError as e:
        logger.warning("⚠️ DB init: %s", e)

    # ── Create AIClient and inject ──
    try:
        from arki_project.utils.ai_client import AIClient
        ai_client = AIClient(
            api_key=settings.ai_api_key or "",
            base_url=settings.ai_base_url,
            model=settings.ai_model,
            max_history=settings.ai_max_history,
            temperature=settings.ai_temperature,
            max_tokens=settings.ai_max_tokens,
            groq_api_key=settings.groq_api_key or "",
            openrouter_api_key=settings.openrouter_api_key or "",
        )
        dp["ai_client"] = ai_client
        logger.info("✅ AIClient created")
    except ArkiBaseError as e:
        logger.warning("⚠️ AIClient: %s", e)
        dp["ai_client"] = None

    # ── Middleware ──
    try:
        from arki_project.middlewares.register import AutoRegisterMiddleware
        dp.message.middleware(AutoRegisterMiddleware())
        dp.callback_query.middleware(AutoRegisterMiddleware())
        logger.info("✅ AutoRegister middleware")
    except ArkiBaseError as e:
        logger.warning("⚠️ Register middleware: %s", e)

    # ══════════════════════════════════════════════════════
    #  ROUTER ORDER:
    #    1. fallback_router — /start, /help
    #    2. common_router — submenu callbacks
    #    3. handler routers — tools, search, image, etc
    #    4. ddg_chat_router — DDG AI fallback (catch-all text)
    #    5. catchall_router — unhandled callbacks
    # ══════════════════════════════════════════════════════

    # ── 1. Fallback /start ──
    fallback_router = Router(name="fallback_start")

    @fallback_router.message(CommandStart())
    async def fallback_start(message: Message, **kwargs) -> None:
        from arki_project.utils.models_registry import MODELS
        name = _escape_md(message.from_user.first_name or "کاربر") if message.from_user else "کاربر"
        n = len(MODELS)
        greeting = (
            f"🧠 *Arki Engine v30 — TITANIUM*\n\n"
            f"سلام {name}! 👋\n\n"
            f"*{n} مدل AI* 🚀\n"
            "*+150 دستور • 10 شخصیت • 16 بخش*\n\n"
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
        try:
            await message.answer(greeting, reply_markup=main_menu_keyboard())
        except ArkiBaseError as e:
            logger.error("❌ /start failed: %s", e)
            await message.answer("🧠 Arki Engine v30\n\nسلام! ربات آماده‌ست.", reply_markup=main_menu_keyboard())

    @fallback_router.message(Command("help"))
    async def fallback_help(message: Message, **kwargs) -> None:
        await message.answer(
            "📋 *راهنما*\n\n"
            "/start — منوی اصلی\n"
            "/model — انتخاب مدل AI\n"
            "/persona — شخصیت AI\n"
            "/search — جستجو\n"
            "/image — ساخت تصویر\n"
            "/settings — تنظیمات\n\n"
            "💬 هر پیامی بفرستید → جواب AI",
            reply_markup=main_menu_keyboard(),
        )

    dp.include_router(fallback_router)

    # ── 2. Submenu handlers ──
    try:
        submenu_files = [
            "ai_chat_submenu", "image_submenu", "tools_submenu",
            "search_submenu", "files__voice_submenu",
            "content_studio_submenu", "content_brain_submenu",
            "sales_engine_submenu", "sales_brain_submenu",
            "marketing_titan_submenu", "platforms_submenu",
            "product_auto_submenu", "automation_submenu",
            "agents_submenu", "victor_ai_submenu",
            "admin_panel_submenu", "settings_submenu",
            "main_menu___back",
        ]
        loaded = 0
        for name in submenu_files:
            try:
                __import__(f"arki_project.handlers.common_pkg.{name}", fromlist=["_"])
                loaded += 1
            except ArkiBaseError as e:
                logger.warning("⚠️ submenu %s: %s", name, e)

        from arki_project.handlers.common_pkg._common import router as common_router
        dp.include_router(common_router)
        logger.info("✅ %d/%d submenus", loaded, len(submenu_files))
    except ArkiBaseError as e:
        logger.warning("⚠️ common_pkg: %s", e)

    # ── 3. Unified command router (ALL /commands) ──
    try:
        from arki_project.handlers.all_commands import router as cmd_router
        dp.include_router(cmd_router)
        logger.info("✅ all_commands router loaded")
    except ArkiBaseError as e:
        logger.warning("⚠️ all_commands: %s", e)

    # ── 3a. Claude Ultra router ──
    try:
        from arki_project.handlers.claude_ultra_cmd import router as claude_ultra_router
        dp.include_router(claude_ultra_router)
        logger.info("✅ claude_ultra_cmd router loaded")
    except Exception as e:
        logger.warning("⚠️ claude_ultra_cmd: %s", e)

    # ── 3c. Video generation router (v30.1) ──
    try:
        from arki_project.handlers.video import router as video_router
        dp.include_router(video_router)
        logger.info("✅ video router loaded")
    except Exception as e:
        logger.warning("⚠️ video: %s", e)

    # ── 3b. Legacy handler routers (best-effort) ──
    for mod_path in [
        "arki_project.extra.router",
    ]:
        try:
            mod = __import__(mod_path, fromlist=["router"])
            if hasattr(mod, "router"):
                dp.include_router(mod.router)
                logger.info("✅ %s", mod_path.split(".")[-1])
        except ArkiBaseError as e:
            logger.warning("⚠️ %s: %s", mod_path.split(".")[-1], e)

    # ── 3d. Action Handlers (makes ALL submenu buttons work) ──
    try:
        from arki_project.handlers.action_handlers import router as action_router
        dp.include_router(action_router)
        logger.info("✅ action_handlers router loaded (%d act: buttons)",
                     len(action_router.callback_query.handlers))
    except Exception as e:
        logger.warning("⚠️ action_handlers: %s", e)

    # ── 4. g4f AI Chat (catch-all text) ──
    ai_router = Router(name="ai_chat")

    @ai_router.message(Command("new"))
    async def cmd_new(message: Message, **kwargs) -> None:
        from arki_project.utils.g4f_provider import clear_history
        uid = message.from_user.id if message.from_user else 0
        clear_history(uid)
        await message.answer("🗑 تاریخچه پاک شد. گفتگوی جدید شروع شد!")

    @ai_router.message(Command("search"))
    async def cmd_search(message: Message, **kwargs) -> None:
        """Web search command."""
        from arki_project.utils.g4f_provider import search_chat
        query = (message.text or "").replace("/search", "", 1).strip()
        if not query:
            await message.answer("🔍 بعد از /search سوالت رو بنویس.\nمثال: `/search آخرین اخبار فنلاند`")
            return
        uid = message.from_user.id if message.from_user else 0
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        status = await message.answer("🔍 در حال جستجو...")
        try:
            answer = await search_chat(uid, query)
            try: await status.delete()
            except: pass
            from arki_project.utils.models_registry import split_for_telegram
            for chunk in split_for_telegram(answer):
                try: await safe_reply(message, chunk)
                except: await message.answer(chunk[:4000], parse_mode=None)
        except ArkiBaseError as e:
            logger.error("Search error: %s", e)
            await safe_edit_text(status, f"❌ خطا: {str(e)[:100]}")

    @ai_router.message(Command("deep"))
    async def cmd_deep(message: Message, **kwargs) -> None:
        """Deep research command."""
        from arki_project.utils.g4f_provider import search_chat
        query = (message.text or "").replace("/deep", "", 1).strip()
        if not query:
            await message.answer("🔬 بعد از /deep موضوعت رو بنویس.\nمثال: `/deep تحلیل بازار AI در ایران`")
            return
        uid = message.from_user.id if message.from_user else 0
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        status = await message.answer("🔬 تحقیق عمیق در حال انجام...")
        try:
            answer = await search_chat(uid, f"تحقیق عمیق و جامع: {query}", timeout=30)
            try: await status.delete()
            except: pass
            from arki_project.utils.models_registry import split_for_telegram
            for chunk in split_for_telegram(answer):
                try: await safe_reply(message, chunk)
                except: await message.answer(chunk[:4000], parse_mode=None)
        except ArkiBaseError as e:
            logger.error("Deep research error: %s", e)
            await safe_edit_text(status, f"❌ خطا: {str(e)[:100]}")

    @ai_router.message()
    async def handle_text_ai(message: Message, **kwargs) -> None:
        """Catch-all text handler — checks pending actions first, then AI chat."""
        if not message.text or not message.text.strip():
            return
        
        text = message.text.strip()
        uid = message.from_user.id if message.from_user else 0
        
        # ── Check for pending button action ──
        from arki_project.utils.user_state import get_pending, clear_pending
        from arki_project.utils.command_engine import execute_command
        pending = get_pending(uid)
        if pending:
            action = pending["action"]
            clear_pending(uid)
            
            await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
            status = await message.answer("🧠 در حال پردازش...")
            
            try:
                answer = await execute_command(uid, action, text, timeout=30)
                try: await status.delete()
                except: pass
                from arki_project.utils.models_registry import split_for_telegram
                for chunk in split_for_telegram(answer):
                    try: await safe_reply(message, chunk)
                    except: await message.answer(chunk[:4000], parse_mode=None)
            except ArkiBaseError as e:
                logger.error("Pending action %s error: %s", action, e)
                await safe_edit_text(status, f"❌ خطا: {str(e)[:100]}")
            return
        
        # ── Normal AI chat ──
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        status = await message.answer("🧠 در حال تفکر...")
        
        try:
            from arki_project.utils.g4f_provider import chat as ai_chat
            
            model_key = ""
            if ai_client:
                try:
                    cfg = await ai_client.get_user_config(uid)
                    model_key = cfg.get("model", "")
                except ArkiBaseError:
                    pass
            
            answer = await ai_chat(user_id=uid, text=text, model_key=model_key, timeout=25)
            
            if not answer or not answer.strip():
                await safe_edit_text(status, "⚠️ پاسخی دریافت نشد. لطفاً دوباره تلاش کنید.")
                return
            
            try: await status.delete()
            except: pass
            
            from arki_project.utils.models_registry import split_for_telegram
            chunks = split_for_telegram(answer)
            for chunk in chunks:
                try: await safe_reply(message, chunk)
                except ArkiBaseError:
                    try: await message.answer(chunk[:4000], parse_mode=None)
                    except: await message.answer(chunk[:4000])
        
        except ArkiBaseError as e:
            logger.error("AI chat error: %s", e)
            await safe_edit_text(status, f"❌ خطا در پردازش: {str(e)[:100]}\n\nلطفاً دوباره تلاش کنید.")

    dp.include_router(ai_router)
    logger.info("✅ g4f AI chat (catch-all text handler)")

    # ── 5. APEX fallback handlers (see run_bot_parts/apex_fallbacks.py) ──
    try:
        from run_bot_parts.apex_fallbacks import register_apex_fallbacks
        await register_apex_fallbacks(dp, bot)
    except Exception as exc:
        logger.warning("APEX fallbacks: %s", exc)

    # ── 6. Catch-all callbacks ──
    catchall_router = Router(name="catchall")

    @catchall_router.callback_query()
    async def catch_all_callback(callback: CallbackQuery, **kwargs) -> None:
        action = callback.data or ""
        logger.info("Unhandled callback: %s from user %s", action, callback.from_user.id)
        await callback.answer(f"🔧 {action} — به‌زودی فعال می‌شه!", show_alert=False)

    dp.include_router(catchall_router)

    # ── Error handler ──
    @dp.error()
    async def error_handler(event: ErrorEvent) -> bool:
        logger.error("Unhandled error: %s: %s", type(event.exception).__name__, event.exception)
        return True

    # ── Start polling ──
    logger.info("🚀 Starting polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())


