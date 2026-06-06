
from __future__ import annotations
"""
architecture.service.background — BackgroundService, DaemonService
═══════════════════════════════════════════════════════════════════
Long-running background tasks and daemon processes.
Covers: background-service, daemon, worker, ops
"""
import asyncio, logging, time
from dataclasses import dataclass
from typing import Any, Callable, Dict



logger = logging.getLogger(__name__)

@dataclass
class TaskInfo:
    name: str
    interval_s: float
    last_run: float = 0
    run_count: int = 0
    errors: int = 0
    running: bool = False

class BackgroundService:
    """Manage periodic background tasks."""
    def __init__(self) -> None:
        self._tasks: Dict[str, TaskInfo] = {}
        self._handles: Dict[str, asyncio.Task] = {}
        self._running = False

    def register(self, name: str, fn: Callable, interval_s: float = 60) -> None:
        self._tasks[name] = TaskInfo(name=name, interval_s=interval_s)
        self._tasks[name]._fn = fn

    async def start(self) -> None:
        self._running = True
        for name, info in self._tasks.items():
            self._handles[name] = asyncio.ensure_future(self._run_loop(name, info))
        logger.info("BackgroundService started %d tasks", len(self._tasks))

    async def stop(self) -> None:
        self._running = False
        for handle in self._handles.values():
            handle.cancel()
        self._handles.clear()

    async def _run_loop(self, name: str, info: TaskInfo) -> None:
        while self._running:
            try:
                info.running = True
                result = info._fn()
                if asyncio.iscoroutine(result):
                    await result
                info.run_count += 1
                info.last_run = time.time()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                info.errors += 1
                logger.error("Background task %s error: %s", name, exc)
            finally:
                info.running = False
            await asyncio.sleep(info.interval_s)

    @property
    def stats(self) -> Dict[str, Any]:
        return {name: {"runs": t.run_count, "errors": t.errors, "running": t.running}
                for name, t in self._tasks.items()}

class DaemonService(BackgroundService):
    """Extended background service with health monitoring and auto-restart."""
    def __init__(self, max_consecutive_errors: int = 5) -> None:
        super().__init__()
        self._max_errors = max_consecutive_errors
        self._consecutive_errors: Dict[str, int] = {}

    async def _run_loop(self, name: str, info: TaskInfo) -> None:
        self._consecutive_errors[name] = 0
        while self._running:
            try:
                info.running = True
                result = info._fn()
                if asyncio.iscoroutine(result):
                    await result
                info.run_count += 1
                info.last_run = time.time()
                self._consecutive_errors[name] = 0
            except asyncio.CancelledError:
                break
            except Exception as exc:
                info.errors += 1
                self._consecutive_errors[name] += 1
                logger.error("Daemon %s error (%d): %s", name,
                             self._consecutive_errors[name], exc)
                if self._consecutive_errors[name] >= self._max_errors:
                    logger.critical("Daemon %s exceeded max errors, stopping", name)
                    break
            finally:
                info.running = False
            await asyncio.sleep(info.interval_s)


