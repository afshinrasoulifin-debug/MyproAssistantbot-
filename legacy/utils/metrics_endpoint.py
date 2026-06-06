
"""
Prometheus Metrics HTTP Endpoint v9.1
Exposes /metrics for Prometheus scraping.
"""
import logging
from aiohttp import web
from typing import Optional, Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

_runner: Optional[web.AppRunner] = None


async def start_metrics_server(port: int = 9090) -> None:
    """Start HTTP server for Prometheus metrics."""
    global _runner

    from arki_project.utils.metrics_collector import get_metrics

    async def metrics_handler(request: Any) -> None:
        metrics = get_metrics()
        return web.Response(
            text=metrics.to_prometheus(),
            content_type="text/plain",
        )

    async def health_handler(request: Any) -> None:
        return web.Response(text="ok", content_type="text/plain")

    async def stats_handler(request: Any) -> None:
        import json
        metrics = get_metrics()
        return web.Response(
            text=json.dumps(metrics.get_all(), default=str, indent=2),
            content_type="application/json",
        )

    app = web.Application()
    app.router.add_get("/metrics", metrics_handler)
    app.router.add_get("/health", health_handler)
    app.router.add_get("/stats", stats_handler)

    _runner = web.AppRunner(app)
    await _runner.setup()
    site = web.TCPSite(_runner, "0.0.0.0", port)
    await site.start()
    logger.info("📊 Metrics endpoint started on port %d", port)


async def stop_metrics_server() -> None:
    global _runner
    if _runner:
        await _runner.cleanup()
        _runner = None


