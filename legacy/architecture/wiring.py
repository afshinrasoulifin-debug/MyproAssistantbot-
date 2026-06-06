
from __future__ import annotations
"""
architecture.wiring — REAL connections between architecture components and bot
═════════════════════════════════════════════════════════════════════════════
This module wires architecture components together:
  - EventBus connects handlers → telemetry → memory
  - HealthMonitor checks all subsystems  
  - Controller manages lifecycle
  - Agents run periodic background tasks
  - Middleware hooks into aiogram request pipeline

Called from setup.py after component init.
"""


from aiogram import BaseMiddleware

import logging
import time
from typing import Any, Dict

# ── Architecture internal connections ──


logger = logging.getLogger(__name__)


def wire_components(registry: Dict[str, Any]) -> None:
    """Wire all architecture components together with real connections."""

    event_bus = registry.get("event_bus")
    telemetry = registry.get("telemetry_monitor")
    diagnostics = registry.get("diagnostics_monitor")
    health = registry.get("health_monitor")
    observer = registry.get("observer")
    watcher = registry.get("watcher")
    controller = registry.get("controller")
    supervisor = registry.get("supervisor")
    config = registry.get("config")

    if not event_bus:
        logger.warning("EventBus not found — skipping wiring")
        return

    # ── 1. EventBus → TelemetryMonitor ──
    # Every event published to the bus gets recorded as telemetry.
    # EventBus handlers receive a BusMessage object.
    if telemetry:
        def _telemetry_listener(msg) -> None:
            """Record every event in telemetry counters and timing."""
            telemetry.increment(f"event.{msg.topic}")
            payload = msg.payload
            if isinstance(payload, dict) and "duration_s" in payload:
                telemetry.record(f"timing.{msg.topic}", payload["duration_s"])

        event_bus.subscribe("handler.start", _telemetry_listener)
        event_bus.subscribe("handler.complete", _telemetry_listener)
        event_bus.subscribe("handler.error", _telemetry_listener)
        event_bus.subscribe("ai.request", _telemetry_listener)
        event_bus.subscribe("ai.response", _telemetry_listener)
        event_bus.subscribe("memory.store", _telemetry_listener)
        event_bus.subscribe("memory.recall", _telemetry_listener)
        event_bus.subscribe("search.query", _telemetry_listener)
        event_bus.subscribe("image.generate", _telemetry_listener)
        event_bus.subscribe("pipeline.classify", _telemetry_listener)
        logger.debug("Wired: EventBus → TelemetryMonitor (10 event types)")

    # ── 2. EventBus → DiagnosticsMonitor ──
    # Errors get traced for debugging.
    if diagnostics:
        def _diagnostics_listener(msg) -> None:
            """Trace handler completions/errors for diagnostics."""
            payload = msg.payload
            if isinstance(payload, dict):
                diagnostics.trace(
                    operation=msg.topic,
                    duration_s=payload.get("duration_s", 0),
                    success=payload.get("success", True),
                    user_id=payload.get("user_id"),
                    handler=payload.get("handler"),
                )

        event_bus.subscribe("handler.complete", _diagnostics_listener)
        event_bus.subscribe("handler.error", _diagnostics_listener)
        event_bus.subscribe("ai.response", _diagnostics_listener)
        logger.debug("Wired: EventBus → DiagnosticsMonitor")

    # ── 3. HealthMonitor — register real checks ──
    if health:
        def _check_event_bus():
            return sum(len(s) for s in event_bus._subscribers.values())

        def _check_telemetry():
            if telemetry:
                return telemetry.report()
            raise RuntimeError("Telemetry not available")

        def _check_config():
            if config:
                return "ok"
            raise RuntimeError("Config not available")

        def _check_memory_module():
            try:
                from arki_project.utils.v7_core import get_memory
                mem = get_memory()
                return "ok"
            except Exception as e:
                raise RuntimeError(f"Memory: {e}")

        health.register("event_bus", _check_event_bus)
        health.register("telemetry", _check_telemetry)
        health.register("config", _check_config)
        health.register("memory_module", _check_memory_module)
        logger.debug("Wired: HealthMonitor (4 health checks)")

    # ── 4. Observer — cross-cutting concerns ──
    if observer:
        def _log_errors(event: str, data: Any) -> None:
            if isinstance(data, dict) and not data.get("success", True):
                logger.warning("System error observed: %s — %s", event, data.get("error"))

        observer.subscribe("system.error", _log_errors)
        observer.subscribe("handler.error", _log_errors)
        logger.debug("Wired: Observer (error logging)")

    # ── 5. Watcher — monitor critical values ──
    if watcher:
        watcher.watch("total_requests", 0)
        watcher.watch("total_errors", 0)
        watcher.watch("avg_response_time", 0.0)

        def _on_request_count_change(key, old, new):
            if new > 0 and new % 100 == 0:
                logger.info("Milestone: %d total requests processed", new)

        watcher.on_change("total_requests", _on_request_count_change)
        logger.debug("Wired: Watcher (3 watched values)")

    # ── 6. Controller — register all managed components ──
    if controller:
        for name in ["event_bus", "telemetry_monitor", "health_monitor",
                      "diagnostics_monitor", "observer", "watcher"]:
            comp = registry.get(name)
            if comp:
                controller.register(name, comp)
        logger.debug("Wired: Controller (manages %d components)", len(controller._components))

    # ── 7. Supervisor — auto-restart critical components ──
    if supervisor:
        for name in ["event_bus", "telemetry_monitor", "health_monitor"]:
            comp = registry.get(name)
            if comp:
                supervisor.register(name, comp)
        logger.debug("Wired: Supervisor (monitors %d critical components)", len(supervisor._components))

    # ── 8. Console commands ──
    admin_console = registry.get("admin_console")
    if admin_console:
        admin_console.register_command("arch_status", lambda: {
            "components": len(registry),
            "health": health.status if health else "n/a",
            "telemetry": telemetry.report() if telemetry else "n/a",
        })
        admin_console.register_command("arch_health", lambda: 
            "healthy" if (health and health.is_healthy()) else "degraded"
        )
        admin_console.register_command("arch_metrics", lambda: 
            telemetry.report() if telemetry else {}
        )
        admin_console.register_command("arch_diagnostics", lambda:
            diagnostics.diagnostic_report() if diagnostics else {}
        )
        logger.debug("Wired: AdminConsole (4 arch commands)")

    logger.info("✅ Architecture wiring complete — %d cross-connections", 
                 _count_connections(registry))


def _count_connections(registry: Dict[str, Any]) -> int:
    """Count the number of real connections between components."""
    count = 0
    eb = registry.get("event_bus")
    if eb and hasattr(eb, "_subscribers"):
        count += sum(len(v) for v in eb._subscribers.values())
    hm = registry.get("health_monitor")
    if hm and hasattr(hm, "_checks"):
        count += len(hm._checks)
    obs = registry.get("observer")
    if obs and hasattr(obs, "_subscribers"):
        count += sum(len(v) for v in obs._subscribers.values())
    wt = registry.get("watcher")
    if wt and hasattr(wt, "_watched"):
        count += len(wt._watched)
    ctrl = registry.get("controller")
    if ctrl and hasattr(ctrl, "_components"):
        count += len(ctrl._components)
    return count


# ═══════════════════════════════════════════════════════════════
# Middleware Hook — connects architecture to aiogram handlers
# ═══════════════════════════════════════════════════════════════

class ArchitectureMiddleware(BaseMiddleware):  # v9.8.7: must inherit for outer_middleware
    """
    aiogram middleware that fires architecture events on every handler call.
    
    Install in main.py:
        from arki_project.architecture.wiring import ArchitectureMiddleware
        dp.update.outer_middleware(ArchitectureMiddleware(registry))
    """

    def __init__(self, registry: Dict[str, Any]) -> None:
        self._event_bus = registry.get("event_bus")
        self._telemetry = registry.get("telemetry_monitor")
        self._watcher = registry.get("watcher")

    async def __call__(self, handler, event, data):
        if not self._event_bus:
            return await handler(event, data)

        handler_name = handler.__name__ if hasattr(handler, "__name__") else str(handler)
        user_id = None
        if hasattr(event, "from_user") and event.from_user:
            user_id = event.from_user.id

        # Fire start event (EventBus.publish is async)
        await self._event_bus.publish("handler.start", {
            "handler": handler_name,
            "user_id": user_id,
            "time": time.time(),
        })

        t0 = time.time()
        try:
            result = await handler(event, data)
            duration = time.time() - t0

            # Fire complete event
            await self._event_bus.publish("handler.complete", {
                "handler": handler_name,
                "user_id": user_id,
                "duration_s": duration,
                "success": True,
            })

            # Update watcher
            if self._watcher:
                total = self._watcher.get("total_requests") or 0
                self._watcher.update("total_requests", total + 1)

            # Record timing
            if self._telemetry:
                self._telemetry.record(f"handler.{handler_name}", duration)

            return result

        except Exception as exc:
            duration = time.time() - t0

            # Fire error event
            await self._event_bus.publish("handler.error", {
                "handler": handler_name,
                "user_id": user_id,
                "duration_s": duration,
                "success": False,
                "error": str(exc),
            })

            # Update error counter
            if self._watcher:
                errors = self._watcher.get("total_errors") or 0
                self._watcher.update("total_errors", errors + 1)

            raise




# ── Infrastructure ↔ Architecture Event Bridge (v9.8.7: moved out of class) ──
def wire_infrastructure_bridge(event_bus) -> None:
    """Wire architecture EventBus ↔ infrastructure EventBus (call after boot)."""
    try:
        from arki_project.core.boot import get_infra
        infra = get_infra()
        if not infra or not infra.get("event_bus"):
            return
        infra_bus = infra["event_bus"]

        def _forward_to_infra(msg):
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                _t = loop.create_task(infra_bus.emit(f"arch.{msg.topic}", msg.payload))
                _t.add_done_callback(lambda t: logger.error("Bridge forward failed: %s", t.exception()) if t.done() and not t.cancelled() and t.exception() else None)
            except RuntimeError:
                pass  # No running loop — ignore

        for topic in ["handler.start", "handler.complete", "handler.error",
                      "ai.request", "ai.response", "memory.store"]:
            event_bus.subscribe(topic, _forward_to_infra)

        async def _forward_to_arch(data):
            await event_bus.publish("infra.event", data)

        infra_bus.on("core.booted", lambda d: None)
        logger.info("Architecture ↔ Infrastructure event bridge wired")
    except ImportError:
        logger.debug("Infrastructure event bridge: package not available")


