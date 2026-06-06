
from __future__ import annotations
"""ComputeNode — Handles computation tasks in the infrastructure grid."""
import asyncio, logging, time
from typing import Any, Callable, Dict



logger = logging.getLogger(__name__)


class ComputeNode:
    """A compute node that can execute tasks in the infrastructure."""

    def __init__(self, name: str = "compute-default", max_concurrent: int = 10) -> None:
        self.name = name
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._task_count = 0
        self._total_time = 0.0
        self._active = True

    async def execute(self, task: Callable, *args, **kwargs) -> Any:
        """Execute a task with concurrency control."""
        async with self._semaphore:
            t0 = time.time()
            try:
                if asyncio.iscoroutinefunction(task):
                    result = await task(*args, **kwargs)
                else:
                    result = task(*args, **kwargs)
                self._task_count += 1
                self._total_time += time.time() - t0
                return result
            except Exception as e:
                logger.error("ComputeNode %s task failed: %s", self.name, e)
                raise

    def stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "tasks_completed": self._task_count,
            "avg_time": self._total_time / max(self._task_count, 1),
            "active": self._active,
        }


