
from __future__ import annotations
"""QueueWorker — Queue-based task processing."""
import asyncio, logging
from typing import Any, Callable



logger = logging.getLogger(__name__)

class QueueWorker:
    """Process tasks from an async queue."""

    def __init__(self, handler: Callable = None, max_size: int = 10000) -> None:
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._handler = handler
        self._running = False
        self._processed = 0

    async def enqueue(self, item: Any) -> Any:
        await self._queue.put(item)

    async def start(self, num_workers: int = 3) -> Any:
        self._running = True
        for i in range(num_workers):
            asyncio.create_task(self._worker(f"qw-{i}"))

    async def _worker(self, name: str) -> Any:
        while self._running:
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=5)
                if self._handler:
                    await self._handler(item)
                self._processed += 1
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("QueueWorker %s: %s", name, e)

    def stop(self) -> Any:
        self._running = False


