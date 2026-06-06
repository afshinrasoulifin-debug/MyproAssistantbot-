
from __future__ import annotations
"""ExecutionRuntime — Sandboxed code execution runtime."""

import asyncio
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)



class ExecutionRuntime:
    """ExecutionRuntime — Sandboxed code execution runtime."""

    def __init__(self, *, name: str = "execution_runtime") -> None:
        self.name = name
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}
        self._context: Dict[str, Any] = {}
        self._stats = {"started": 0, "stopped": 0, "errors": 0}
        logger.info("ExecutionRuntime '%s' initialized", name)

    async def start(self) -> None:
        """Start the runtime."""
        if self._running:
            return
        self._running = True
        self._stats["started"] += 1
        logger.info("ExecutionRuntime '%s' started", self.name)

    async def stop(self) -> None:
        """Stop the runtime and cancel tasks."""
        self._running = False
        for tid, task in self._tasks.items():
            if not task.done():
                task.cancel()
        self._tasks.clear()
        self._stats["stopped"] += 1
        logger.info("ExecutionRuntime '%s' stopped", self.name)

    async def submit(self, task_id: str, coro: Any) -> Dict:
        """Submit a coroutine to run in this runtime."""
        if not self._running:
            return {"ok": False, "error": "Runtime not started"}

        try:
            task = asyncio.create_task(coro)
            self._tasks[task_id] = task
            return {"ok": True, "task_id": task_id}
        except Exception as e:
            self._stats["errors"] += 1
            return {"ok": False, "error": str(e)}

    def set_context(self, key: str, value: Any) -> None:
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        return self._context.get(key, default)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def active_tasks(self) -> int:
        return sum(1 for t in self._tasks.values() if not t.done())

    def get_status(self) -> Dict:
        return {
            "name": self.name,
            "running": self._running,
            "active_tasks": self.active_tasks,
            "total_tasks": len(self._tasks),
            "stats": self._stats,
        }


