
"""
admin_pkg/_health_new.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ──────────── /health (NEW) ────────────

@router.message(Command("health"))
async def cmd_health(message: Message, settings: Settings) -> None:
    """System health check."""
    if not message.from_user or not _is_admin(message.from_user.id, settings):
        await message.answer("🚫 فقط ادمین.")
        return

    try:
        db = await health_check()
        from arki_project.utils.http_pool import pool_stats
        pools = pool_stats()

        uptime = format_duration(int(_time.monotonic() - _BOT_START_TIME))

        pool_lines = []
        for name, stats in pools.items():
            status = "🟢" if stats["alive"] else "⚪"
            pool_lines.append(
                f"  {status} {name}: {stats['requests']} req / {stats['errors']} err"
            )

        db_status = "🟢" if db.get("ok") else "🔴"
        db_size = db.get("details", {}).get("size_mb", "?")
        db_tables = db.get("details", {}).get("table_count", "?")

        text = (
            f"🏥 *سلامت سیستم — v{_VERSION}*\n\n"
            f"⏱ آپتایم: `{uptime}`\n\n"
            "*💾 دیتابیس:*\n"
            f"  {db_status} وضعیت: {db.get('message', '?')}\n"
            f"  📦 حجم: {db_size} MB\n"
            f"  🗂 تعداد جداول: {db_tables}\n\n"
            "*🌐 HTTP Pools:*\n" + "\n".join(pool_lines) + "\n\n"
            "*🔑 Provider ها:*\n"
            f"  Gemini: {'✅' if settings.ai_api_key else '❌'}\n"
            f"  Groq: {'✅' if settings.groq_api_key else '❌'}\n"
            f"  OpenRouter: {'✅' if settings.openrouter_api_key else '❌'}\n\n"
            "*⚙️ تنظیمات:*\n"
            f"  Log Level: `{settings.log_level}`\n"
            f"  Rate Limit: {settings.rate_limit_messages}/{settings.rate_limit_window}s\n"
            f"  Maintenance: {'🔧 فعال' if settings.maintenance_mode else '❌'}\n"
            f"  Analytics: {'✅' if settings.analytics_enabled else '❌'}"
        )
        await send_long_text(message, text)

    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(f"❌ خطا: {exc}")





