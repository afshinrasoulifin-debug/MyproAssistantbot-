
#!/usr/bin/env python3
"""
Synthetic monitoring for Arki Engine — v10.1 (TITANIUM-enhanced)
Runs periodic health checks and reports issues.
"""
import asyncio
import aiohttp
import logging
import os
import time

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("synthetic_monitor")

HEALTH_URL = os.environ.get("HEALTH_URL", "http://localhost:8443/health")
READY_URL = os.environ.get("READY_URL", "http://localhost:8443/ready")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "60"))
ALERT_WEBHOOK = os.environ.get("ALERT_WEBHOOK", "")


async def check_endpoint(session, url: str, name: str) -> dict:
    """Check a single endpoint — TITANIUM-first with aiohttp fallback."""
    start = time.monotonic()
    try:
        # v10.1: TITANIUM shielded check
        if _TITANIUM_ACTIVE:
            ti_resp = await shielded_get(url, timeout=10.0)
            latency = (time.monotonic() - start) * 1000
            body = ti_resp.json() if ti_resp.success else {}
            return {
                "name": name,
                "status": ti_resp.status,
                "latency_ms": round(latency, 2),
                "ok": ti_resp.status == 200,
                "body": body,
                "via": "titanium",
            }
        # Fallback: raw aiohttp
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            latency = (time.monotonic() - start) * 1000
            body = await resp.json()
            return {
                "name": name,
                "status": resp.status,
                "latency_ms": round(latency, 2),
                "ok": resp.status == 200,
                "body": body,
                "via": "aiohttp",
            }
    except Exception as e:
        return {
            "name": name,
            "status": 0,
            "latency_ms": -1,
            "ok": False,
            "error": str(e),
        }


async def send_alert(message: str):
    """Send alert via webhook (Slack, Discord, etc.) — TITANIUM-first."""
    if not ALERT_WEBHOOK:
        logger.warning("ALERT (no webhook): %s", message)
        return
    payload = {"text": f"🚨 Arki Alert: {message}"}
    # v10.1: TITANIUM shielded alert
    if _TITANIUM_ACTIVE:
        await shielded_post(ALERT_WEBHOOK, json_data=payload, timeout=10.0)
        return
    # Fallback
    async with aiohttp.ClientSession() as session:
        await session.post(ALERT_WEBHOOK, json=payload)


async def monitor_loop():
    """Main monitoring loop."""
    logger.info("Starting synthetic monitor (interval=%ds, titanium=%s)",
                CHECK_INTERVAL, _TITANIUM_ACTIVE)
    consecutive_failures = 0

    async with aiohttp.ClientSession() as session:
        while True:
            results = await asyncio.gather(
                check_endpoint(session, HEALTH_URL, "health"),
                check_endpoint(session, READY_URL, "ready"),
            )

            all_ok = all(r["ok"] for r in results)

            for r in results:
                status = "✅" if r["ok"] else "❌"
                via = r.get("via", "unknown")
                logger.info("%s %s: status=%d latency=%.1fms via=%s",
                           status, r["name"], r["status"], r.get("latency_ms", -1), via)

            if not all_ok:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    failed = [r["name"] for r in results if not r["ok"]]
                    await send_alert(f"Endpoints failing ({consecutive_failures}x): {', '.join(failed)}")
            else:
                if consecutive_failures >= 3:
                    await send_alert("✅ All endpoints recovered")
                consecutive_failures = 0

            await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(monitor_loop())


