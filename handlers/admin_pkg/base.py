
"""
admin_pkg/base.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa

@router.message(Command("ping"))
async def cmd_ping(message: Message, settings: Settings) -> None:
    """Health check — available to everyone, detailed for admins."""
    user_id = message.from_user.id  # type: ignore[union-attr]
    if not _is_admin(user_id, settings):
        await message.answer("🏓 Pong!")
        return

    uptime_s = int(_time.monotonic() - _BOT_START_TIME)
    db_health = await health_check()
    db_status = "✅" if db_health.get("ok") else "❌"
    db_size = db_health.get("details", {}).get("size_mb", "?")

    await safe_reply(message,
        "🏓 *Pong!*\n\n"
        f"⏱ آپتایم: `{format_duration(uptime_s)}`\n"
        f"🤖 Arki Engine v{_VERSION}\n"
        f"{db_status} دیتابیس: {db_size} MB\n"
        "✅ تمام سیستم‌ها عملیاتی",
    )





