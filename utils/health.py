
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/health.py
──────────────────────
Lightweight health check server for monitoring.
Runs on a separate port (default 8080) for uptime monitoring.

Usage: Set HEALTH_PORT env var (default: 8080).
Responds to GET /health with JSON status.
"""


import logging
import time
from aiohttp import web

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

_start_time = time.monotonic()
_app: web.Application | None = None
_runner: web.AppRunner | None = None


async def _handle_health(request: web.Request) -> web.Response:
    """Health check endpoint."""
    uptime = int(time.monotonic() - _start_time)
    return web.json_response({
        "status": "ok",
        "uptime_seconds": uptime,
        "version": "7.0",
    })


async def start_health_server(port: int = 8080) -> bool:
    """Start a minimal HTTP health check server."""
    global _app, _runner
    try:
        _app = web.Application()
        _app.router.add_get("/health", _handle_health)
        _runner = web.AppRunner(_app)
        await _runner.setup()
        site = web.TCPSite(_runner, "0.0.0.0", port)
        await site.start()
        logger.info("✅ Health check server running on port %d", port)
        return True
    except ArkiBaseError as exc:
        logger.warning("Health server failed to start: %s", exc)
        return False


async def stop_health_server() -> None:
    """Stop the health check server."""
    global _runner
    if _runner:
        await _runner.cleanup()
        _runner = None


