
"""
Minimal Arki Engine runner — boots only working handlers.
Bypasses broken split packages to get the bot running ASAP.
"""
import asyncio
import logging
import os
import sys

# Ensure env vars are set
os.environ.setdefault("BOT_TOKEN", "8973741555:AAEnTYLlCerm-4xNFfGBIAexmCyHtNxi98A")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///data/arki.db")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("TZ", "Asia/Tehran")

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from arki_project.config import load_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("arki.minimal")


async def main():
    settings = load_settings()
    logger.info("🧠 Arki Engine v30 — Minimal Runner")
    logger.info("   Token: %s...", settings.bot_token[:10])

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()

    # ── 0. Register essential middlewares ──
    try:
        from arki_project.middlewares.register import AutoRegisterMiddleware
        dp.message.middleware(AutoRegisterMiddleware())
        dp.callback_query.middleware(AutoRegisterMiddleware())
        logger.info("✅ AutoRegister middleware loaded")
    except Exception as e:
        logger.warning("⚠️ AutoRegister middleware: %s", e)

    # Inject settings into handler data
    dp["settings"] = settings

    # ── 1. Load common handlers (menu + submenus) ──
    try:
        from arki_project.handlers.common_pkg import router as common_router
        dp.include_router(common_router)
        logger.info("✅ common_pkg router loaded (menus + submenus)")
    except Exception as e:
        logger.error("❌ common_pkg: %s", e, exc_info=True)

    # ── 2. Try loading individual handler modules ──
    handler_modules = [
        ("arki_project.handlers.ai_chat", "ai_chat"),
        ("arki_project.handlers.tools", "tools"),
        ("arki_project.handlers.search", "search"),
        ("arki_project.handlers.image", "image"),
        ("arki_project.handlers.voice", "voice"),
        ("arki_project.handlers.files", "files"),
        ("arki_project.handlers.models_cmd", "models_cmd"),
        ("arki_project.handlers.create", "create"),
        ("arki_project.handlers.poster", "poster"),
        ("arki_project.extra.router", "extra"),
    ]

    for mod_path, name in handler_modules:
        try:
            mod = __import__(mod_path, fromlist=["router"])
            if hasattr(mod, "router"):
                dp.include_router(mod.router)
                logger.info("✅ %s loaded", name)
            else:
                logger.warning("⚠️ %s has no router", name)
        except Exception as e:
            logger.warning("⚠️ %s skipped: %s", name, e)

    # ── 3. Database initialization ──
    try:
        from arki_project.database.connection import init_db
        await init_db(settings.database_url)
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.warning("⚠️ DB init: %s", e)

    # ── 4. Start polling ──
    logger.info("🚀 Starting polling...")
    try:
        # Delete webhook to enable polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())


