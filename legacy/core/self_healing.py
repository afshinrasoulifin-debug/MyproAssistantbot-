
from __future__ import annotations
"""
core/self_healing.py — Self-Healing Infrastructure Engine v10.4.1
═══════════════════════════════════════════════════════════════════
Enterprise-grade self-healing system that monitors, detects failures,
and automatically recovers infrastructure components.

Features:
  - Component lifecycle management (start, stop, restart, health check)
  - Dependency-aware restart ordering (DAG topology sort)
  - Cascade failure prevention (circuit breaker per component)
  - Exponential backoff on repeated failures
  - Recovery hooks for custom healing logic
  - Health history with trend analysis
  - Watchdog timer for stuck components
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Deque, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ComponentState(Enum):
    UNKNOWN = "unknown"
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    RECOVERING = "recovering"
    DEAD = "dead"
    STOPPED = "stopped"


@dataclass
class HealthRecord:
    """Single health check result."""
    ts: float
    state: ComponentState
    latency_ms: float
    message: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComponentSpec:
    """Specification for a managed component."""
    name: str
    health_fn: Optional[Callable[[], Coroutine]] = None     # async () -> bool | dict
    start_fn: Optional[Callable[[], Coroutine]] = None      # async () -> None
    stop_fn: Optional[Callable[[], Coroutine]] = None       # async () -> None
    restart_fn: Optional[Callable[[], Coroutine]] = None    # async () -> None
    recovery_hooks: List[Callable] = field(default_factory=list)  # Custom recovery logic
    depends_on: List[str] = field(default_factory=list)      # Dependencies
    # Tuning
    check_interval_sec: float = 30.0
    failure_threshold: int = 3       # Consecutive failures before recovery
    max_restarts: int = 5            # Max restarts before marking DEAD
    restart_backoff_base: float = 5.0  # Base backoff in seconds
    restart_backoff_max: float = 300.0  # Max backoff
    watchdog_timeout_sec: float = 60.0  # Max time for a health check


@dataclass
class ComponentStatus:
    """Runtime status of a managed component."""
    spec: ComponentSpec
    state: ComponentState = ComponentState.UNKNOWN
    consecutive_failures: int = 0
    total_restarts: int = 0
    last_check_ts: float = 0.0
    last_healthy_ts: float = 0.0
    last_restart_ts: float = 0.0
    health_history: Deque[HealthRecord] = field(default_factory=lambda: deque(maxlen=100))
    uptime_start: float = 0.0

    @property
    def uptime_seconds(self) -> float:
        if self.state in (ComponentState.HEALTHY, ComponentState.DEGRADED) and self.uptime_start > 0:
            return time.time() - self.uptime_start
        return 0.0

    @property
    def health_trend(self) -> str:
        """Analyze recent health trend: improving, stable, degrading."""
        if len(self.health_history) < 5:
            return "insufficient_data"
        recent = list(self.health_history)[-10:]
        healthy = sum(1 for r in recent if r.state == ComponentState.HEALTHY)
        ratio = healthy / len(recent)
        if ratio >= 0.8:
            return "stable"
        elif ratio >= 0.5:
            return "degrading"
        else:
            return "critical"

    @property
    def avg_latency_ms(self) -> float:
        if not self.health_history:
            return 0.0
        return sum(r.latency_ms for r in self.health_history) / len(self.health_history)


class SelfHealingEngine:
    """Monitors and automatically heals infrastructure components.

    Usage:
        engine = SelfHealingEngine()
        engine.register(ComponentSpec(
            name="database",
            health_fn=check_db_health,
            restart_fn=restart_db,
        ))
        engine.register(ComponentSpec(
            name="cache",
            health_fn=check_cache,
            depends_on=["database"],
        ))
        await engine.start()  # Starts monitoring loop
    """

    def __init__(self, check_interval: float = 15.0) -> None:
        self._components: Dict[str, ComponentStatus] = {}
        self._global_interval = check_interval
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._cascade_lock = asyncio.Lock()
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._stats = {
            "total_checks": 0,
            "total_failures": 0,
            "total_recoveries": 0,
            "total_restarts": 0,
            "cascade_preventions": 0,
        }

    # ── Registration ──

    def register(self, spec: ComponentSpec) -> None:
        """Register a component for monitoring."""
        self._components[spec.name] = ComponentStatus(spec=spec)
        logger.info("Self-healing: registered component '%s' (deps=%s)",
                     spec.name, spec.depends_on)

    def unregister(self, name: str) -> bool:
        return self._components.pop(name, None) is not None

    # ── Event Hooks ──

    def on_event(self, event_type: str, handler: Callable) -> None:
        """Register handler for events: 'failure', 'recovery', 'restart', 'dead', 'cascade'."""
        self._event_handlers[event_type].append(handler)

    async def _emit(self, event_type: str, component: str, **kwargs) -> Any:
        for handler in self._event_handlers.get(event_type, []):
            try:
                result = handler(component, **kwargs)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error("Event handler error for %s/%s: %s", event_type, component, e)

    # ── Lifecycle ──

    async def start(self) -> Any:
        """Start the monitoring loop."""
        if self._running:
            return
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(), name="self_healing_monitor")
        logger.info("Self-healing engine started (%d components)", len(self._components))

    async def stop(self) -> Any:
        """Stop the monitoring loop."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Self-healing engine stopped")

    # ── Core Monitor Loop ──

    async def _monitor_loop(self) -> Any:
        while self._running:
            try:
                # Check all components in dependency order
                order = self._topological_sort()
                for name in order:
                    if not self._running:
                        break
                    status = self._components.get(name)
                    if not status or status.state == ComponentState.STOPPED:
                        continue
                    await self._check_component(status)
                await asyncio.sleep(self._global_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Self-healing monitor error: %s", e)
                await asyncio.sleep(5)

    async def _check_component(self, status: ComponentStatus) -> Any:
        """Check a single component's health."""
        spec = status.spec
        self._stats["total_checks"] += 1

        if not spec.health_fn:
            return

        t0 = time.time()
        try:
            # Watchdog timeout
            result = await asyncio.wait_for(
                spec.health_fn(),
                timeout=spec.watchdog_timeout_sec,
            )

            latency_ms = (time.time() - t0) * 1000

            # Parse result
            if isinstance(result, bool):
                is_healthy = result
                message = ""
                metrics = {}
            elif isinstance(result, dict):
                is_healthy = result.get("healthy", result.get("ok", True))
                message = result.get("message", "")
                metrics = result.get("metrics", {})
            else:
                is_healthy = bool(result)
                message = ""
                metrics = {}

            record = HealthRecord(
                ts=time.time(), latency_ms=latency_ms,
                state=ComponentState.HEALTHY if is_healthy else ComponentState.UNHEALTHY,
                message=message, metrics=metrics,
            )
            status.health_history.append(record)
            status.last_check_ts = time.time()

            if is_healthy:
                if status.state != ComponentState.HEALTHY:
                    old_state = status.state
                    status.state = ComponentState.HEALTHY
                    status.uptime_start = time.time()
                    if old_state in (ComponentState.UNHEALTHY, ComponentState.RECOVERING):
                        self._stats["total_recoveries"] += 1
                        await self._emit("recovery", spec.name, old_state=old_state.value)
                        logger.info("✅ Component '%s' recovered (was %s)", spec.name, old_state.value)
                status.consecutive_failures = 0
            else:
                await self._handle_failure(status, message)

        except asyncio.TimeoutError:
            latency_ms = (time.time() - t0) * 1000
            record = HealthRecord(
                ts=time.time(), latency_ms=latency_ms,
                state=ComponentState.UNHEALTHY, message="watchdog_timeout",
            )
            status.health_history.append(record)
            await self._handle_failure(status, "watchdog timeout")
        except Exception as e:
            latency_ms = (time.time() - t0) * 1000
            record = HealthRecord(
                ts=time.time(), latency_ms=latency_ms,
                state=ComponentState.UNHEALTHY, message=str(e)[:200],
            )
            status.health_history.append(record)
            await self._handle_failure(status, str(e))

    async def _handle_failure(self, status: ComponentStatus, reason: str) -> None:
        """Handle a component failure."""
        spec = status.spec
        status.consecutive_failures += 1
        self._stats["total_failures"] += 1

        await self._emit("failure", spec.name,
                          consecutive=status.consecutive_failures, reason=reason)

        if status.consecutive_failures >= spec.failure_threshold:
            if status.total_restarts >= spec.max_restarts:
                status.state = ComponentState.DEAD
                logger.critical("💀 Component '%s' marked DEAD after %d restarts",
                                spec.name, status.total_restarts)
                await self._emit("dead", spec.name, total_restarts=status.total_restarts)
            else:
                # Check cascade: don't restart if dependencies are down
                async with self._cascade_lock:
                    deps_healthy = await self._check_dependencies(spec)
                    if deps_healthy:
                        await self._restart_component(status)
                    else:
                        self._stats["cascade_preventions"] += 1
                        status.state = ComponentState.DEGRADED
                        logger.warning("⚠️ Component '%s' degraded — dependencies unhealthy, "
                                       "skipping restart", spec.name)
                        await self._emit("cascade", spec.name)
        else:
            status.state = ComponentState.UNHEALTHY

    async def _restart_component(self, status: ComponentStatus) -> Any:
        """Restart a component with exponential backoff."""
        spec = status.spec
        status.state = ComponentState.RECOVERING

        # Calculate backoff
        backoff = min(
            spec.restart_backoff_base * (2 ** status.total_restarts),
            spec.restart_backoff_max,
        )

        logger.warning("🔄 Restarting '%s' (attempt %d, backoff %.1fs)",
                        spec.name, status.total_restarts + 1, backoff)
        await asyncio.sleep(backoff)

        try:
            # Run recovery hooks first
            for hook in spec.recovery_hooks:
                try:
                    r = hook(spec.name)
                    if asyncio.iscoroutine(r):
                        await r
                except Exception as e:
                    logger.error("Recovery hook failed for '%s': %s", spec.name, e)

            # Restart
            if spec.restart_fn:
                await asyncio.wait_for(spec.restart_fn(), timeout=spec.watchdog_timeout_sec)
            elif spec.stop_fn and spec.start_fn:
                try:
                    await asyncio.wait_for(spec.stop_fn(), timeout=15)
                except Exception as _err:
                    logger.warning("Suppressed error: %s", _err)
                await asyncio.wait_for(spec.start_fn(), timeout=spec.watchdog_timeout_sec)

            status.total_restarts += 1
            status.consecutive_failures = 0
            status.last_restart_ts = time.time()
            self._stats["total_restarts"] += 1
            await self._emit("restart", spec.name, attempt=status.total_restarts)
            logger.info("✅ Component '%s' restarted successfully", spec.name)

        except Exception as e:
            status.total_restarts += 1
            logger.error("❌ Restart failed for '%s': %s", spec.name, e)

    async def _check_dependencies(self, spec: ComponentSpec) -> bool:
        """Check if all dependencies of a component are healthy."""
        for dep_name in spec.depends_on:
            dep = self._components.get(dep_name)
            if not dep or dep.state not in (ComponentState.HEALTHY, ComponentState.DEGRADED):
                return False
        return True

    # ── Topology Sort ──

    def _topological_sort(self) -> List[str]:
        """Sort components by dependency order."""
        visited: Set[str] = set()
        result: List[str] = []

        def visit(name: str) -> Any:
            if name in visited:
                return
            visited.add(name)
            status = self._components.get(name)
            if status:
                for dep in status.spec.depends_on:
                    visit(dep)
            result.append(name)

        for name in self._components:
            visit(name)
        return result

    # ── Manual Controls ──

    async def restart(self, name: str) -> bool:
        """Manually restart a component."""
        status = self._components.get(name)
        if not status:
            return False
        await self._restart_component(status)
        return True

    async def check_now(self, name: str) -> Optional[Dict]:
        """Run an immediate health check."""
        status = self._components.get(name)
        if not status:
            return None
        await self._check_component(status)
        return self.get_component_status(name)

    def mark_healthy(self, name: str) -> Any:
        """Manually mark a component healthy (e.g., after manual fix)."""
        status = self._components.get(name)
        if status:
            status.state = ComponentState.HEALTHY
            status.consecutive_failures = 0
            status.uptime_start = time.time()

    # ── Status & Dashboard ──

    def get_component_status(self, name: str) -> Optional[Dict]:
        status = self._components.get(name)
        if not status:
            return None
        return {
            "name": name,
            "state": status.state.value,
            "consecutive_failures": status.consecutive_failures,
            "total_restarts": status.total_restarts,
            "uptime_seconds": round(status.uptime_seconds, 1),
            "health_trend": status.health_trend,
            "avg_latency_ms": round(status.avg_latency_ms, 1),
            "last_check": status.last_check_ts,
            "last_healthy": status.last_healthy_ts,
            "depends_on": status.spec.depends_on,
        }

    def dashboard(self) -> Dict:
        """Full health dashboard."""
        components = {}
        for name in self._topological_sort():
            components[name] = self.get_component_status(name)

        healthy = sum(1 for s in self._components.values()
                      if s.state == ComponentState.HEALTHY)
        total = len(self._components)

        return {
            "engine_running": self._running,
            "total_components": total,
            "healthy": healthy,
            "unhealthy": total - healthy,
            "health_ratio": round(healthy / max(1, total), 2),
            "stats": dict(self._stats),
            "components": components,
        }

    @property
    def is_system_healthy(self) -> bool:
        """Quick check: are all registered components healthy?"""
        return all(
            s.state in (ComponentState.HEALTHY, ComponentState.UNKNOWN, ComponentState.STOPPED)
            for s in self._components.values()
        )


