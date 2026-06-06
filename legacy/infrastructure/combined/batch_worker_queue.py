
from __future__ import annotations
"""
BatchWorkerQueue — Combines batch processing + worker pool + queue.
"""
import asyncio, logging
from typing import Any, Callable, List



logger = logging.getLogger(__name__)

class BatchWorkerQueue:
    """Queue-based batch processing with worker pool."""

    def __init__(self, num_workers: int = 5, batch_size: int = 10) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
        self._num_workers = num_workers
        self._batch_size = batch_size
        self._handler: Callable = None
        self._processed = 0

    def set_handler(self, fn: Callable) -> None:
        self._handler = fn

    async def submit(self, item: Any) -> Any:
        await self._queue.put(item)

    async def submit_batch(self, items: List[Any]) -> Any:
        for item in items:
            await self._queue.put(item)

    async def start(self) -> Any:
        for i in range(self._num_workers):
            _t = asyncio.create_task(self._worker(f"bwq-{i}"))
            _t.add_done_callback(lambda t: logger.error('Task failed: %s', t.exception()) if t.done() and not t.cancelled() and t.exception() else None)

    async def _worker(self, name: str) -> Any:
        while True:
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=5)
                if self._handler:
                    await self._handler(item)
                self._processed += 1
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue


