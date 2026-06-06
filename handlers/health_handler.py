
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
handlers/health_handler.py — System Health Command v3.3
═══════════════════════════════════════════════════════════════
/health — Real-time system status dashboard for admins.
Shows all component health, key rotation status, queue depth, etc.
"""
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

logger = logging.getLogger(__name__)
router = Router(name="health_handler")

STATUS_EMOJI = {
    "ok": "✅", "healthy": "✅", "ready": "✅", "active": "✅",
    "running": "🟢", "degraded": "🟡", "error": "🔴", "critical": "🔴",
    "not_configured": "⚪",
}

@router.message(Command("health"))
async def cmd_health(message: Message) -> None:
    """Show real-time system health dashboard."""
    try:
        from arki_project.utils.system_health import get_system_health
        health = get_system_health()
        report = await health.full_check()

        status = report.get("status", "unknown")
        emoji = STATUS_EMOJI.get(status, "❓")

        lines = [
            f"{emoji} *System Health: {status.upper()}*",
            f"⏱ Uptime: {report.get('uptime_seconds', 0) // 60}m",
            f"🐍 Python: {report.get('python_version', '?')}",
            "",
        ]

        for comp, data in report.get("components", {}).items():
            comp_status = data.get("status", "unknown")
            comp_emoji = STATUS_EMOJI.get(comp_status, "❓")
            detail = ""
            if comp == "key_manager":
                providers = data.get("providers", {})
                detail = f" — {sum(p.get('total_keys', 0) for p in providers.values())} keys"
            elif comp == "request_queue":
                detail = f" — pending: {data.get('pending', 0)}"
            elif comp == "event_bus":
                detail = f" — {data.get('published', 0)} events"
            elif comp == "automation":
                detail = f" — {data.get('custom_rules', 0)} rules"
            elif comp == "marketing":
                detail = f" — {data.get('total_leads', 0)} leads"

            lines.append(f"  {comp_emoji} {comp}{detail}")

        await message.reply("\n".join(lines), parse_mode="Markdown")

    except HandlerError as e:
        await message.reply(f"⚠️ Health check error: {e}")


def get_router() -> Router:
    return router


