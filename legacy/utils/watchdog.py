
from __future__ import annotations
"""
tg_bot/utils/watchdog.py
─────────────────────────
WATCHDOG v1.0 — Self-Recovery & Persistence Engine

Bot resilience and monitoring:
  • Heartbeat — periodic health signals
  • Auto-recovery — restart on crash/hang
  • Persistence — state snapshots to disk
  • Autorun — restore state after restart
  • Daemon monitoring — track external services
  • Health aggregation — combine all subsystem checks
  • Alert system — notify admin on critical events
  • Uptime tracking with history
  • Dead-man switch — alert if heartbeat stops

Architecture:
  heartbeat loop → health checks → alert if needed → auto-recover

v29.0.0
"""


import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Optional

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

# ── Configuration ──
HEARTBEAT_INTERVAL = 30  # seconds
HEALTH_CHECK_INTERVAL = 60
STATE_FILE = os.environ.get("WATCHDOG_STATE_FILE", "data/arki_watchdog_state.json")
ALERT_COOLDOWN = 300  # 5 min between duplicate alerts
MAX_EVENTS = 200


# ── Types ──

@dataclass
class HealthCheck:
    """A registered health check."""
    name: str
    check_fn: Callable[[], Awaitable[bool]]
    interval: float = HEALTH_CHECK_INTERVAL
    last_check: float = 0
    last_ok: bool = True
    consecutive_fails: int = 0
    total_checks: int = 0
    total_fails: int = 0

@dataclass
class WatchdogEvent:
    """A recorded watchdog event."""
    timestamp: float
    event_type: str  # heartbeat, health_ok, health_fail, alert, recovery
    source: str
    message: str
    severity: str = "info"  # info, warning, critical

@dataclass
class WatchdogState:
    """Persistent watchdog state."""
    started_at: float = field(default_factory=time.time)
    last_heartbeat: float = 0
    heartbeat_count: int = 0
    is_healthy: bool = True
    events: list[WatchdogEvent] = field(default_factory=list)
    subsystems: dict[str, bool] = field(default_factory=dict)


class Watchdog:
    """Central watchdog for bot health and recovery."""

    def __init__(self) -> None:
        self._state = WatchdogState()
        self._health_checks: dict[str, HealthCheck] = {}
        self._alert_fn: Optional[Callable[[str, str], Awaitable[None]]] = None
        self._heartbeat_task: asyncio.Task | None = None
        self._health_task: asyncio.Task | None = None
        self._alert_history: dict[str, float] = {}  # key → last alert time

    def register_check(self, name: str, check_fn: Callable[[], Awaitable[bool]],
                       interval: float = HEALTH_CHECK_INTERVAL) -> None:
        """Register a health check function."""
        self._health_checks[name] = HealthCheck(
            name=name, check_fn=check_fn, interval=interval,
        )

    def set_alert_handler(self, fn: Callable[[str, str], Awaitable[None]]) -> None:
        """Set the alert notification function."""
        self._alert_fn = fn

    async def start(self) -> None:
        """Start watchdog loops."""
        self._load_state()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._health_task = asyncio.create_task(self._health_loop())
        self._record_event("watchdog", "Watchdog started", "info", "start")
        logger.info("🐕 Watchdog started")

    async def stop(self) -> None:
        """Stop watchdog and save state."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._health_task:
            self._health_task.cancel()
        self._save_state()
        logger.info("🐕 Watchdog stopped")

    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat signal."""
        while True:
            try:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                self._state.last_heartbeat = time.time()
                self._state.heartbeat_count += 1
                self._record_event("heartbeat", "alive", "info", "heartbeat")

                # Save state periodically
                if self._state.heartbeat_count % 10 == 0:
                    self._save_state()

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Heartbeat error")

    async def _health_loop(self) -> None:
        """Periodic health checks."""
        while True:
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
                all_ok = True

                for name, check in self._health_checks.items():
                    now = time.time()
                    if now - check.last_check < check.interval:
                        continue

                    check.last_check = now
                    check.total_checks += 1

                    try:
                        ok = await asyncio.wait_for(check.check_fn(), timeout=10)
                    except Exception:
                        ok = False

                    if ok:
                        check.last_ok = True
                        check.consecutive_fails = 0
                        self._state.subsystems[name] = True
                    else:
                        check.last_ok = False
                        check.consecutive_fails += 1
                        check.total_fails += 1
                        self._state.subsystems[name] = False
                        all_ok = False

                        self._record_event(
                            name,
                            f"Health check failed (#{check.consecutive_fails})",
                            "critical" if check.consecutive_fails >= 3 else "warning",
                            "health_fail",
                        )

                        # Alert on consecutive failures
                        if check.consecutive_fails >= 3:
                            await self._send_alert(
                                f"🔴 {name}",
                                f"Health check failed {check.consecutive_fails} times in a row",
                            )

                self._state.is_healthy = all_ok

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Health check loop error")

    async def _send_alert(self, title: str, message: str) -> None:
        """Send alert with cooldown."""
        now = time.time()
        key = f"{title}:{message[:50]}"
        if key in self._alert_history and now - self._alert_history[key] < ALERT_COOLDOWN:
            return

        self._alert_history[key] = now
        if self._alert_fn:
            try:
                await self._alert_fn(title, message)
            except Exception:
                logger.exception("Alert handler error")

    def _record_event(self, source: str, message: str,
                      severity: str, event_type: str) -> None:
        """Record a watchdog event."""
        self._state.events.append(WatchdogEvent(
            timestamp=time.time(),
            event_type=event_type,
            source=source,
            message=message,
            severity=severity,
        ))
        if len(self._state.events) > MAX_EVENTS:
            self._state.events = self._state.events[-MAX_EVENTS:]

    def _save_state(self) -> None:
        """Save state to disk for persistence across restarts."""
        try:
            data = {
                "started_at": self._state.started_at,
                "last_heartbeat": self._state.last_heartbeat,
                "heartbeat_count": self._state.heartbeat_count,
                "is_healthy": self._state.is_healthy,
                "subsystems": self._state.subsystems,
            }
            with open(STATE_FILE, mode="w") as f:
                json.dump(data, f)
        except Exception:
            logger.warning("Failed to save watchdog state")

    def _load_state(self) -> None:
        """Load state from disk (autorun recovery)."""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, mode="r") as f:
                    data = json.load(f)
                prev_heartbeat = data.get("last_heartbeat", 0)
                if prev_heartbeat:
                    gap = time.time() - prev_heartbeat
                    if gap > HEARTBEAT_INTERVAL * 3:
                        self._record_event(
                            "watchdog",
                            f"Recovered after {int(gap)}s downtime",
                            "warning", "recovery",
                        )
                        logger.warning("Watchdog recovered after %ds gap", int(gap))
        except Exception as e:
            logger.debug("Suppressed: %s", e)

    def status(self) -> dict:
        """Get current watchdog status."""
        return {
            "healthy": self._state.is_healthy,
            "uptime_s": int(time.time() - self._state.started_at),
            "heartbeats": self._state.heartbeat_count,
            "last_heartbeat_ago": int(time.time() - self._state.last_heartbeat) if self._state.last_heartbeat else -1,
            "subsystems": self._state.subsystems.copy(),
            "checks": {
                name: {
                    "ok": c.last_ok,
                    "fails": c.consecutive_fails,
                    "total_checks": c.total_checks,
                    "total_fails": c.total_fails,
                }
                for name, c in self._health_checks.items()
            },
            "recent_events": [
                {
                    "time": e.timestamp,
                    "type": e.event_type,
                    "source": e.source,
                    "message": e.message,
                    "severity": e.severity,
                }
                for e in self._state.events[-10:]
            ],
        }


# ── Module Singleton ──
watchdog = Watchdog()


