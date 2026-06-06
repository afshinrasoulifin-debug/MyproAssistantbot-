
from __future__ import annotations
"""AsyncWorker — Async task processing worker."""
import asyncio, logging
from typing import Any, Callable, List



logger = logging.getLogger(__name__)

class AsyncWorker:
    """Process tasks asynchronously with concurrency control."""

    def __init__(self, name: str = "worker", concurrency: int = 10) -> None:
        self.name = name
        self._sem = asyncio.Semaphore(concurrency)
        self._tasks: List[asyncio.Task] = []
        self._completed = 0
        self._failed = 0

    async def submit(self, fn: Callable, *args, **kwargs) -> Any:
        async with self._sem:
            try:
                result = await fn(*args, **kwargs) if asyncio.iscoroutinefunction(fn) else fn(*args, **kwargs)
                self._completed += 1
                return result
            except Exception as e:
                self._failed += 1
                logger.error("Worker %s: task failed: %s", self.name, e)
                raise

    async def submit_batch(self, fn: Callable, items: list) -> list:
        tasks = [asyncio.create_task(self.submit(fn, item)) for item in items]
        return await asyncio.gather(*tasks, return_exceptions=True)

    @property
    def stats(self) -> Any:
        return {"completed": self._completed, "failed": self._failed, "pending": len(self._tasks)}


