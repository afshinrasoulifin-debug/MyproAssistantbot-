
"""
admin_pkg/_maintenance_new.py — Arki Engine v29.0.0
"""
from ._common import *  # noqa

# ──────────── /maintenance (NEW) ────────────

@router.message(Command("maintenance"))
async def cmd_maintenance(message: Message, settings: Settings) -> None:
    """Toggle maintenance mode."""
    if not message.from_user or not _is_admin(message.from_user.id, settings):
        await message.answer("🚫 فقط ادمین.")
        return

    from arki_project.middlewares.maintenance import MaintenanceMiddleware

    MaintenanceMiddleware.active = not MaintenanceMiddleware.active
    status = "فعال 🔧" if MaintenanceMiddleware.active else "غیرفعال ✅"
    await safe_reply(message, f"🔧 حالت تعمیرات: *{status}*")
    logger.info(
        "Admin %d toggled maintenance mode: %s",
        message.from_user.id, MaintenanceMiddleware.active,
    )





