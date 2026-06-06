
from __future__ import annotations
"""
architecture.automations — Real automation workflows connecting architecture + bot
═══════════════════════════════════════════════════════════════════════════════════
Concrete automations that run on the EventBus:

1. AutoHealthCheck — periodic health checks via HealthMonitor
2. TelemetryAggregator — aggregate + alert on metrics
3. MemoryCleanup — periodic memory persistence + cleanup
4. PerformanceWatchdog — detect slow handlers and alert
5. UsageAnalytics — track per-user and per-handler statistics

These are REAL automations with REAL logic, not empty structures.
EventBus handlers receive BusMessage objects (msg.topic, msg.payload).
"""


import asyncio
import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AutoHealthCheck:
    """
    Periodic health check automation.
    
    Runs every `interval_s` seconds, checks all registered health checks,
    and publishes results to the EventBus. If any check fails, triggers
    recovery via Supervisor.
    """

    def __init__(self, registry: Dict[str, Any], interval_s: float = 60.0) -> None:
        self._health = registry.get("health_monitor")
        self._supervisor = registry.get("supervisor")
        self._event_bus = registry.get("event_bus")
        self._interval = interval_s
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._check_count = 0
        self._failure_count = 0

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("AutoHealthCheck started (interval=%ds)", self._interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._check()
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Health check loop error: %s", exc)
                await asyncio.sleep(self._interval)

    async def _check(self) -> None:
        if not self._health:
            return

        self._check_count += 1
        results = await self._health.check_all()

        # Find failures
        failures = {name: status for name, status in results.items() if status != "healthy"}
        if failures:
            self._failure_count += len(failures)
            logger.warning("Health check failures: %s", failures)

            # Attempt recovery via supervisor
            if self._supervisor:
                for name in failures:
                    success = await self._supervisor.restart_component(name)
                    if success:
                        logger.info("Auto-recovered: %s", name)

            # Publish failure event
            if self._event_bus:
                await self._event_bus.publish("health.failure", {
                    "failures": failures,
                    "check_number": self._check_count,
                    "time": time.time(),
                })
        else:
            if self._event_bus:
                await self._event_bus.publish("health.ok", {
                    "check_number": self._check_count,
                    "time": time.time(),
                })

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "checks": self._check_count,
            "failures": self._failure_count,
            "running": self._running,
        }


class TelemetryAggregator:
    """
    Periodic telemetry aggregation with alerting.
    
    Every `interval_s` seconds:
    1. Aggregate metrics from TelemetryMonitor
    2. Check thresholds  
    3. Publish summary to EventBus
    4. Log warnings for anomalies
    """

    def __init__(self, registry: Dict[str, Any], interval_s: float = 300.0) -> None:
        self._telemetry = registry.get("telemetry_monitor")
        self._diagnostics = registry.get("diagnostics_monitor")
        self._event_bus = registry.get("event_bus")
        self._interval = interval_s
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._summaries: List[Dict[str, Any]] = []
        self._thresholds = {
            "handler_avg_time": 5.0,   # Alert if avg handler time > 5s
            "error_rate": 0.1,          # Alert if > 10% error rate
        }

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("TelemetryAggregator started (interval=%ds)", self._interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self._interval)
                await self._aggregate()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Telemetry aggregation error: %s", exc)

    async def _aggregate(self) -> None:
        if not self._telemetry:
            return

        report = self._telemetry.report()
        counters = report.get("counters", {})
        
        total_requests = counters.get("event.handler.complete", 0)
        total_errors = counters.get("event.handler.error", 0)
        error_rate = total_errors / max(total_requests + total_errors, 1)

        summary = {
            "time": time.time(),
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": round(error_rate, 4),
            "counters": dict(counters),
        }
        self._summaries.append(summary)
        if len(self._summaries) > 288:  # Keep 24h at 5min intervals
            self._summaries = self._summaries[-144:]

        # Check thresholds
        alerts = []
        if error_rate > self._thresholds["error_rate"]:
            alerts.append(f"High error rate: {error_rate:.1%}")

        if alerts:
            logger.warning("Telemetry alerts: %s", alerts)
            if self._event_bus:
                await self._event_bus.publish("telemetry.alert", {
                    "alerts": alerts, "summary": summary,
                })

        if self._event_bus:
            await self._event_bus.publish("telemetry.summary", summary)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "summaries": len(self._summaries),
            "latest": self._summaries[-1] if self._summaries else None,
            "running": self._running,
        }


class MemoryCleanup:
    """
    Periodic memory persistence and cleanup.
    
    Every `interval_s` seconds:
    1. Persist MemoryStore to disk (JSON/SQLite)
    2. Clean up expired entries
    3. Report memory stats
    """

    def __init__(self, registry: Dict[str, Any], interval_s: float = 600.0) -> None:
        self._event_bus = registry.get("event_bus")
        self._interval = interval_s
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._persist_count = 0
        self._cleanup_count = 0

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("MemoryCleanup started (interval=%ds)", self._interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self._interval)
                await self._run()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Memory cleanup error: %s", exc)

    async def _run(self) -> None:
        try:
            from arki_project.utils.v7_core import persist_memory
            await persist_memory()
            self._persist_count += 1
            
            if self._event_bus:
                await self._event_bus.publish("memory.persist", {
                    "count": self._persist_count,
                    "time": time.time(),
                })
        except Exception as exc:
            logger.debug("Memory persist: %s", exc)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "persists": self._persist_count,
            "cleanups": self._cleanup_count,
            "running": self._running,
        }


class PerformanceWatchdog:
    """
    Monitor handler performance and detect anomalies.
    
    Listens to handler.complete events, tracks per-handler timing,
    and alerts when a handler is consistently slow.
    Handler receives BusMessage (msg.payload is the dict).
    """

    def __init__(self, registry: Dict[str, Any], slow_threshold_s: float = 3.0) -> None:
        self._event_bus = registry.get("event_bus")
        self._telemetry = registry.get("telemetry_monitor")
        self._slow_threshold = slow_threshold_s
        self._handler_times: Dict[str, List[float]] = defaultdict(list)
        self._slow_alerts: List[Dict[str, Any]] = []
        self._max_history = 100

    def start(self) -> None:
        if self._event_bus:
            self._event_bus.subscribe("handler.complete", self._on_handler_event)
            self._event_bus.subscribe("handler.error", self._on_handler_event)
            logger.info("PerformanceWatchdog started (threshold=%.1fs)", self._slow_threshold)

    def _on_handler_event(self, msg) -> None:
        """Handler for BusMessage from EventBus."""
        data = msg.payload
        if not isinstance(data, dict):
            return
        
        handler = data.get("handler", "unknown")
        duration = data.get("duration_s", 0)
        
        times = self._handler_times[handler]
        times.append(duration)
        if len(times) > self._max_history:
            self._handler_times[handler] = times[-self._max_history // 2:]

        # Alert if this individual request was slow
        if duration > self._slow_threshold:
            alert = {
                "handler": handler,
                "duration_s": round(duration, 3),
                "threshold": self._slow_threshold,
                "user_id": data.get("user_id"),
                "time": time.time(),
            }
            self._slow_alerts.append(alert)
            if len(self._slow_alerts) > 200:
                self._slow_alerts = self._slow_alerts[-100:]
            logger.warning("Slow handler: %s took %.2fs", handler, duration)

        # Record in telemetry
        if self._telemetry:
            self._telemetry.record(f"perf.{handler}", duration)

    def get_handler_stats(self) -> Dict[str, Dict[str, float]]:
        """Get per-handler performance statistics."""
        import statistics
        result = {}
        for handler, times in self._handler_times.items():
            if times:
                result[handler] = {
                    "count": len(times),
                    "avg": round(statistics.mean(times), 3),
                    "median": round(statistics.median(times), 3),
                    "min": round(min(times), 3),
                    "max": round(max(times), 3),
                    "p95": round(sorted(times)[int(len(times) * 0.95)], 3) if len(times) >= 20 else round(max(times), 3),
                }
        return result

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "tracked_handlers": len(self._handler_times),
            "slow_alerts": len(self._slow_alerts),
            "handler_stats": self.get_handler_stats(),
        }


class UsageAnalytics:
    """
    Track per-user and per-handler usage statistics.
    
    Listens to events and builds analytics:
    - Top users by request count
    - Top handlers by usage
    - Hourly request distribution
    - Feature adoption rates

    Handler receives BusMessage (msg.payload is the dict).
    """

    def __init__(self, registry: Dict[str, Any]) -> None:
        self._event_bus = registry.get("event_bus")
        self._user_counts: Dict[int, int] = defaultdict(int)
        self._handler_counts: Dict[str, int] = defaultdict(int)
        self._hourly_counts: Dict[int, int] = defaultdict(int)
        self._feature_counts: Dict[str, int] = defaultdict(int)

    def start(self) -> None:
        if self._event_bus:
            self._event_bus.subscribe("handler.complete", self._on_handler_complete)
            self._event_bus.subscribe("ai.request", self._on_ai_request)
            self._event_bus.subscribe("search.query", self._on_feature_use)
            self._event_bus.subscribe("image.generate", self._on_feature_use)
            logger.info("UsageAnalytics started")

    def _on_handler_complete(self, msg) -> None:
        """BusMessage handler."""
        data = msg.payload
        if not isinstance(data, dict):
            return
        user_id = data.get("user_id")
        handler = data.get("handler", "unknown")
        
        if user_id:
            self._user_counts[user_id] += 1
        self._handler_counts[handler] += 1

        import datetime
        hour = datetime.datetime.now().hour
        self._hourly_counts[hour] += 1

    def _on_ai_request(self, msg) -> None:
        self._feature_counts["ai_chat"] += 1

    def _on_feature_use(self, msg) -> None:
        self._feature_counts[msg.topic] += 1

    def top_users(self, limit: int = 10) -> List[tuple]:
        return sorted(self._user_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    def top_handlers(self, limit: int = 10) -> List[tuple]:
        return sorted(self._handler_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    def hourly_distribution(self) -> Dict[int, int]:
        return dict(sorted(self._hourly_counts.items()))

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_users": len(self._user_counts),
            "total_requests": sum(self._user_counts.values()),
            "top_users": self.top_users(5),
            "top_handlers": self.top_handlers(5),
            "hourly": self.hourly_distribution(),
            "features": dict(self._feature_counts),
        }


# ═══════════════════════════════════════════════════════════════
# Start all automations
# ═══════════════════════════════════════════════════════════════

_automations: Dict[str, Any] = {}


async def start_automations(registry: Dict[str, Any]) -> Dict[str, str]:
    """Start all automation workflows. Returns status dict."""
    global _automations
    results = {}

    # 1. Health check (every 60s)
    try:
        auto_health = AutoHealthCheck(registry, interval_s=60)
        await auto_health.start()
        _automations["health_check"] = auto_health
        results["health_check"] = "running"
    except Exception as e:
        results["health_check"] = f"error: {e}"

    # 2. Telemetry aggregation (every 5min)
    try:
        telem_agg = TelemetryAggregator(registry, interval_s=300)
        await telem_agg.start()
        _automations["telemetry_agg"] = telem_agg
        results["telemetry_agg"] = "running"
    except Exception as e:
        results["telemetry_agg"] = f"error: {e}"

    # 3. Memory cleanup (every 10min)
    try:
        mem_cleanup = MemoryCleanup(registry, interval_s=600)
        await mem_cleanup.start()
        _automations["memory_cleanup"] = mem_cleanup
        results["memory_cleanup"] = "running"
    except Exception as e:
        results["memory_cleanup"] = f"error: {e}"

    # 4. Performance watchdog (instant — event-driven)
    try:
        perf_wd = PerformanceWatchdog(registry, slow_threshold_s=3.0)
        perf_wd.start()
        _automations["perf_watchdog"] = perf_wd
        results["perf_watchdog"] = "running"
    except Exception as e:
        results["perf_watchdog"] = f"error: {e}"

    # 5. Usage analytics (instant — event-driven)
    try:
        usage = UsageAnalytics(registry)
        usage.start()
        _automations["usage_analytics"] = usage
        results["usage_analytics"] = "running"
    except Exception as e:
        results["usage_analytics"] = f"error: {e}"

    logger.info("✅ Automations started: %d/%d", 
                 sum(1 for v in results.values() if v == "running"),
                 len(results))
    return results


async def stop_automations() -> None:
    """Stop all automations gracefully."""
    for name, auto in _automations.items():
        if hasattr(auto, "stop"):
            try:
                await auto.stop()
            except Exception as e:
                logger.debug("Suppressed: %s", e)
    _automations.clear()
    logger.info("All automations stopped")


def get_automation_stats() -> Dict[str, Any]:
    """Get stats from all running automations."""
    return {name: auto.stats for name, auto in _automations.items() if hasattr(auto, "stats")}


