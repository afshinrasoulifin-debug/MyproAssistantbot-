
from __future__ import annotations
"""
architecture.core.bootstrap — Bootstrapper, Initializer
════════════════════════════════════════════════════════
System bootstrap and initialization sequence.

Covers: bootstrap, initializer, daemon, startup
"""


import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class BootStep:
    name: str
    init_fn: Callable
    priority: int = 50
    required: bool = True
    timeout_s: float = 30.0
    status: str = "pending"
    duration_s: float = 0.0
    error: Optional[str] = None


class Initializer:
    """Ordered initialization of system components."""

    def __init__(self) -> None:
        self._steps: List[BootStep] = []
        self._completed: List[str] = []

    def register(
        self, name: str, fn: Callable, priority: int = 50,
        required: bool = True, timeout_s: float = 30.0,
    ) -> None:
        self._steps.append(BootStep(
            name=name, init_fn=fn, priority=priority,
            required=required, timeout_s=timeout_s,
        ))

    async def run(self) -> Dict[str, Any]:
        sorted_steps = sorted(self._steps, key=lambda s: s.priority)
        results = {}
        for step in sorted_steps:
            t0 = time.time()
            try:
                result = step.init_fn()
                if asyncio.iscoroutine(result):
                    await asyncio.wait_for(result, timeout=step.timeout_s)
                step.status = "ok"
                step.duration_s = time.time() - t0
                self._completed.append(step.name)
            except Exception as exc:
                step.status = "error"
                step.error = str(exc)
                step.duration_s = time.time() - t0
                if step.required:
                    logger.error("REQUIRED init step '%s' failed: %s", step.name, exc)
                    raise
                logger.warning("Optional init step '%s' failed: %s", step.name, exc)
            results[step.name] = {
                "status": step.status,
                "duration_s": round(step.duration_s, 3),
                "error": step.error,
            }
        return results


class Bootstrapper:
    """
    Full system bootstrap — orchestrates initializer, runtime, and daemon setup.
    """

    def __init__(self) -> None:
        self.initializer = Initializer()
        self._daemons: List[Tuple[str, Callable, float]] = []
        self._boot_time: Optional[float] = None
        self._boot_results: Dict[str, Any] = {}

    def add_step(self, name: str, fn: Callable, priority: int = 50, **kw) -> None:
        self.initializer.register(name, fn, priority, **kw)

    def add_daemon(self, name: str, coro_fn: Callable, interval_s: float = 60) -> None:
        self._daemons.append((name, coro_fn, interval_s))

    async def boot(self) -> Dict[str, Any]:
        t0 = time.time()
        logger.info("🚀 Bootstrap starting...")

        self._boot_results = await self.initializer.run()

        # Start daemons
        from .runtime import get_runtime
        rt = get_runtime()
        for name, fn, interval in self._daemons:
            rt.schedule_background(name, fn, interval)
            self._boot_results[f"daemon:{name}"] = {"status": "started", "interval_s": interval}

        self._boot_time = time.time() - t0
        logger.info(
            "✅ Bootstrap complete in %.2fs — %d steps, %d daemons",
            self._boot_time, len(self.initializer._steps), len(self._daemons),
        )
        return {
            "boot_time_s": round(self._boot_time, 3),
            "steps": self._boot_results,
        }

    @property
    def is_booted(self) -> bool:
        return self._boot_time is not None

    @property
    def report(self) -> Dict[str, Any]:
        return {
            "booted": self.is_booted,
            "boot_time_s": round(self._boot_time, 3) if self._boot_time else None,
            "steps": self._boot_results,
        }


# ── Singleton ──
_bootstrapper: Optional[Bootstrapper] = None

def get_bootstrapper() -> Bootstrapper:
    global _bootstrapper
    if _bootstrapper is None:
        _bootstrapper = Bootstrapper()
    return _bootstrapper


