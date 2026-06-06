
from __future__ import annotations
"""BackgroundWorker — Long-running background task worker."""
import asyncio, logging
from typing import Callable, Dict, Any



logger = logging.getLogger(__name__)

class BackgroundWorker:
    """Run long-lived background tasks."""

    def __init__(self) -> None:
        self._tasks: Dict[str, asyncio.Task] = {}

    def start(self, name: str, coro_fn: Callable) -> Any:
        if name in self._tasks and not self._tasks[name].done():
            return
        self._tasks[name] = asyncio.create_task(coro_fn())
        logger.info("BackgroundWorker: started %s", name)

    def stop(self, name: str) -> Any:
        task = self._tasks.get(name)
        if task and not task.done():
            task.cancel()

    def stop_all(self) -> None:
        for task in self._tasks.values():
            if not task.done():
                task.cancel()

    @property
    def running(self) -> list:
        return [n for n, t in self._tasks.items() if not t.done()]


