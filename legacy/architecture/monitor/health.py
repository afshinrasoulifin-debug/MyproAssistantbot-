
from __future__ import annotations
"""
architecture.monitor.health — HealthMonitor, Watcher, Observer
═══════════════════════════════════════════════════════════════
System health monitoring with watches and observers.
Covers: health, watcher, observer
"""
import asyncio, logging, time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional



logger = logging.getLogger(__name__)

@dataclass
class HealthCheck:
    name: str
    check_fn: Callable
    interval_s: float = 30.0
    last_check: float = 0
    last_status: str = "unknown"
    last_error: Optional[str] = None
    consecutive_failures: int = 0

class HealthMonitor:
    """Monitor system health with periodic checks."""
    def __init__(self) -> None:
        self._checks: Dict[str, HealthCheck] = {}
        self._on_unhealthy: List[Callable] = []

    def register(self, name: str, check_fn: Callable, interval_s: float = 30.0) -> None:
        self._checks[name] = HealthCheck(name=name, check_fn=check_fn, interval_s=interval_s)

    def on_unhealthy(self, callback: Callable) -> None:
        self._on_unhealthy.append(callback)

    async def check_all(self) -> Dict[str, str]:
        results = {}
        for name, check in self._checks.items():
            try:
                result = check.check_fn()
                if asyncio.iscoroutine(result):
                    result = await result
                check.last_status = "healthy"
                check.last_error = None
                check.consecutive_failures = 0
            except Exception as exc:
                check.last_status = "unhealthy"
                check.last_error = str(exc)
                check.consecutive_failures += 1
                for cb in self._on_unhealthy:
                    try: cb(name, str(exc))
                    except Exception as _exc:
                        logger.debug("Suppressed: %s", _exc)
            pass
            check.last_check = time.time()
            results[name] = check.last_status
        return results

    def is_healthy(self) -> bool:
        return all(c.last_status == "healthy" for c in self._checks.values())

    @property
    def status(self) -> Dict[str, Any]:
        return {name: {"status": c.last_status, "failures": c.consecutive_failures,
                        "error": c.last_error}
                for name, c in self._checks.items()}

class Watcher:
    """Watch specific values and trigger on change."""
    def __init__(self) -> None:
        self._watched: Dict[str, Any] = {}
        self._callbacks: Dict[str, List[Callable]] = {}

    def watch(self, key: str, initial_value: Any = None) -> None:
        self._watched[key] = initial_value
        self._callbacks.setdefault(key, [])

    def on_change(self, key: str, callback: Callable) -> None:
        self._callbacks.setdefault(key, []).append(callback)

    def update(self, key: str, new_value: Any) -> bool:
        old = self._watched.get(key)
        if old != new_value:
            self._watched[key] = new_value
            for cb in self._callbacks.get(key, []):
                try: cb(key, old, new_value)
                except Exception as _exc:
                    logger.debug("Suppressed: %s", _exc)
            pass
            return True
        return False

    def get(self, key: str) -> Any:
        return self._watched.get(key)

class Observer:
    """Observer pattern for subscribing to events."""
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event: str, callback: Callable) -> None:
        self._subscribers.setdefault(event, []).append(callback)

    def unsubscribe(self, event: str, callback: Callable) -> bool:
        subs = self._subscribers.get(event, [])
        if callback in subs:
            subs.remove(callback)
            return True
        return False

    async def notify(self, event: str, data: Any = None) -> int:
        count = 0
        for cb in self._subscribers.get(event, []):
            try:
                result = cb(event, data)
                if asyncio.iscoroutine(result):
                    await result
                count += 1
            except Exception as exc:
                logger.error("Observer notify error: %s", exc)
        return count


