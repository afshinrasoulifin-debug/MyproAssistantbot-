
#!/usr/bin/env python3
"""Health check script for Arki Engine."""
import sys
import os
import asyncio


import logging
logger = logging.getLogger(__name__)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def health_check():
    checks = {}

    # 1. Config
    try:
        from config import BOT_TOKEN, GEMINI_API_KEY
        checks["config"] = bool(BOT_TOKEN and GEMINI_API_KEY)
    except Exception:
        checks["config"] = False

    # 2. Database
    try:
        from database.connection import async_session
        async with async_session() as session:
            await session.execute("SELECT 1")
        checks["database"] = True
    except Exception:
        checks["database"] = False

    # 3. Modules
    try:
        from core.pipeline import get_pipeline
        checks["pipeline"] = get_pipeline() is not None
    except Exception:
        checks["pipeline"] = False

    # 4. Redis connectivity (v10.3)
    redis_url = os.environ.get("REDIS_URL", "")
    if redis_url:
        try:
            import socket
            # Quick TCP check to Redis port
            parts = redis_url.replace("redis://", "").split(":")
            host = parts[0] if parts else "localhost"
            port_str = parts[1].split("/")[0] if len(parts) > 1 else "6379"
            s = socket.create_connection((host, int(port_str)), timeout=3)
            s.close()
            checks["redis"] = True
        except Exception:
            checks["redis"] = False
    else:
        checks["redis"] = None  # Not configured

    # 5. Disk space (v10.3 addition)
    try:
        import shutil as _shutil
        total, used, free = _shutil.disk_usage(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        free_pct = (free / total) * 100
        checks["disk_space"] = free_pct > 5
        if free_pct < 5:
            logger.info(f"  ⚠️ Disk space low: {free_pct:.1f}% free")
    except Exception:
        checks["disk_space"] = True  # Non-critical

    # 6. Victor brain (v10.3 addition)
    try:
        brain_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "victor_brain")
        if os.path.isdir(brain_dir):
            checks["victor_brain"] = True
        else:
            checks["victor_brain"] = None  # Not yet initialized, not an error
    except Exception:
        checks["victor_brain"] = None

    # 7. Log directory writable (v10.3 addition)
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        os.makedirs(log_dir, exist_ok=True)
        test_file = os.path.join(log_dir, ".health_check_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        checks["log_writable"] = True
    except Exception:
        checks["log_writable"] = False

    # 8. Memory usage (v10.3 addition)
    try:
        import resource
        mem_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        checks["memory"] = mem_mb < 1500  # Under 1.5GB
    except Exception:
        checks["memory"] = True  # Non-critical

    # Print results
    real_checks = {k: v for k, v in checks.items() if v is not None}
    all_ok = all(real_checks.values())
    for name, status in checks.items():
        if status is None:
            icon = "⏭️"
            state = "skipped"
        elif status:
            icon = "✅"
            state = "ok"
        else:
            icon = "❌"
            state = "FAIL"
        logger.info(f"  {icon} {name}: {state}")

    # v10.3.1: JSON output for k8s readiness/liveness probes
    if "--json" in sys.argv:
        import json as _json_out
        result = {
            "status": "healthy" if all_ok else "unhealthy",
            "checks": {
                k: ("ok" if v else ("skip" if v is None else "fail"))
                for k, v in checks.items()
            },
        }
        logger.info(str(_json_out.dumps(result)))
        return 0 if all_ok else 1

    logger.info(f"\nOverall: {'HEALTHY' if all_ok else 'UNHEALTHY'}")
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(health_check()))


