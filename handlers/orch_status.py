
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
tg_bot/handlers/orch_status.py — Orchestration status command
═══════════════════════════════════════════════════════════════
/orchstatus — Shows orchestration layer health, metrics, and status.
Admin-only (checks admin_ids from settings).
"""

import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config 
except ImportError:
    pass
logger = logging.getLogger(__name__)
router = Router(name="orch_status")


@router.message(Command("orchstatus"))
async def cmd_orchstatus(message: Message, **kwargs) -> None:
    """Show orchestration layer status dashboard."""
    settings = kwargs.get("settings") or message.bot.get("settings")
    if settings and hasattr(settings, "admin_ids"):
        if message.from_user.id not in settings.admin_ids:
            await message.answer("⛔ فقط ادمین‌ها دسترسی دارند.")
            return

    try:
        from arki_project.orchestration import get_orchestrator
        orch = get_orchestrator()
        status = orch.get_status()

        dash = status["dashboard"]
        health = status["health"]
        cache = status["cache"]
        queue = status["queue"]
        breakers = status["circuit_breakers"]
        lb = status["load_balancer"]

        lines = [
            "🎼 *Orchestration Status*",
            f"Status: `{health.get('status', '?')}`",
            f"Uptime: `{dash.get('uptime_seconds', 0)}s`",
            "",
            "📊 *Requests*",
            f"Total: `{dash.get('total_requests', 0)}`",
            f"Errors: `{dash.get('total_errors', 0)}`",
            f"Cache hits: `{dash.get('total_cached', 0)}`",
            f"Error rate: `{dash.get('error_rate', 0)}`",
            f"Cache hit rate: `{dash.get('cache_hit_rate', 0)}`",
            f"RPS: `{dash.get('requests_per_second', 0)}`",
        ]

        # Providers
        providers = dash.get("providers", {})
        if providers:
            lines.append("")
            lines.append("🔌 *Providers*")
            for name, info in providers.items():
                lines.append(
                    f"  `{name}`: {info.get('requests', 0)} reqs, "
                    f"{info.get('errors', 0)} err, "
                    f"avg {info.get('avg_latency_ms', 0):.0f}ms"
                )

        # Circuit breakers
        if breakers:
            lines.append("")
            lines.append("⚡ *Circuit Breakers*")
            for name, info in breakers.items():
                emoji = "🟢" if info["state"] == "closed" else (
                    "🔴" if info["state"] == "open" else "🟡"
                )
                lines.append(
                    f"  {emoji} `{name}`: {info['state']} "
                    f"({info['failures']} failures)"
                )

        # Cache
        inf_cache = cache.get("inference", {})
        lines.append("")
        lines.append("💾 *Cache*")
        lines.append(
            f"  Inference: {inf_cache.get('size', 0)}/{inf_cache.get('max_size', 0)} "
            f"(hit rate: {inf_cache.get('hit_rate', 0):.1%})"
        )

        # Queue
        lines.append("")
        lines.append("📋 *Queue*")
        lines.append(
            f"  Size: {queue.get('queue_size', 0)}/{queue.get('max_queue', 0)}, "
            f"Active: {queue.get('active_jobs', 0)}, "
            f"Workers: {queue.get('workers', 0)}"
        )

        await message.answer("\n".join(lines), parse_mode="Markdown")

    except RuntimeError:
        await message.answer("⚠️ Orchestration layer is not booted.")
    except HandlerError as e:
        logger.error("orchstatus error: %s", e)
        await message.answer(f"❌ Error: `{e}`")


