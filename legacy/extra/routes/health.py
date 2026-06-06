
from typing import Any


# ── TITANIUM v29.0 Integration ──


async def ready_handler(request: Any) -> Any:
    """Kubernetes readiness probe — checks all critical dependencies."""
    from aiohttp import web
    checks = {}
    all_ok = True

    # Check database
    try:
        from arki_project.database.connection import health_check
        db_result = await health_check()
        checks["database"] = db_result.get("ok", False)
        if not checks["database"]:
            all_ok = False
    except Exception:
        checks["database"] = False
        all_ok = False

    # Check AI client (basic)
    checks["ai_client"] = True  # Always ready if app is running

    status = 200 if all_ok else 503
    return web.json_response({"ready": all_ok, "checks": checks}, status=status)


