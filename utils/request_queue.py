
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/request_queue.py — Internal Request Queue v3.3
═══════════════════════════════════════════════════════════════
Priority-based async request queue with concurrency control,
deduplication, retry logic, and backpressure management.
Decouples request submission from API execution.
"""
import asyncio, logging, time, hashlib, uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)

class Priority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4

@dataclass(order=True)
class QueueItem:
    priority: int
    created_at: float = field(compare=True)
    item_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12], compare=False)
    key: str = field(default="", compare=False)
    payload: Dict[str, Any] = field(default_factory=dict, compare=False)
    callback: Optional[Callable] = field(default=None, compare=False)
    max_retries: int = field(default=3, compare=False)
    retries: int = field(default=0, compare=False)
    timeout_s: float = field(default=30.0, compare=False)
    result: Any = field(default=None, compare=False)
    error: Optional[str] = field(default=None, compare=False)
    status: str = field(default="queued", compare=False)
    started_at: float = field(default=0.0, compare=False)
    completed_at: float = field(default=0.0, compare=False)

class RequestQueue:
    """Async priority queue with concurrency limiting and dedup."""

    def __init__(self, max_concurrent: int = 10, max_size: int = 10000,
                 dedup_window_s: float = 5.0) -> None:
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_size)
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._dedup_window = dedup_window_s
        self._recent_keys: Dict[str, float] = {}
        self._results: Dict[str, QueueItem] = {}
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._processor: Optional[Callable] = None
        self._stats = {
            "enqueued": 0, "processed": 0, "succeeded": 0,
            "failed": 0, "deduplicated": 0, "retried": 0,
            "rejected_full": 0,
        }

    def set_processor(self, fn: Callable[[QueueItem], Coroutine]) -> None:
        """Set the async function that processes each queue item."""
        self._processor = fn

    async def enqueue(self, payload: Dict[str, Any],
                     priority: Priority = Priority.NORMAL,
                     dedup_key: str = "",
                     callback: Optional[Callable] = None,
                     timeout_s: float = 30.0) -> Optional[str]:
        """Add item to queue. Returns item_id or None if deduplicated."""
        # Dedup check
        key = dedup_key or hashlib.sha256(str(sorted(payload.items())).encode()).hexdigest()[:16]
        now = time.time()
        if key in self._recent_keys and (now - self._recent_keys[key]) < self._dedup_window:
            self._stats["deduplicated"] += 1
            return None

        item = QueueItem(
            priority=priority, created_at=now, key=key,
            payload=payload, callback=callback, timeout_s=timeout_s,
        )
        try:
            self._queue.put_nowait(item)
            self._recent_keys[key] = now
            self._stats["enqueued"] += 1
            return item.item_id
        except asyncio.QueueFull:
            self._stats["rejected_full"] += 1
            logger.warning("Queue full, rejecting request")
            return None

    async def _worker(self, worker_id: int) -> None:
        while self._running:
            try:
                item: QueueItem = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue

            async with self._semaphore:
                item.status = "processing"
                item.started_at = time.time()
                self._stats["processed"] += 1

                try:
                    if self._processor:
                        item.result = await asyncio.wait_for(
                            self._processor(item), timeout=item.timeout_s
                        )
                    item.status = "completed"
                    item.completed_at = time.time()
                    self._stats["succeeded"] += 1

                    if item.callback:
                        try:
                            cb_result = item.callback(item)
                            if asyncio.iscoroutine(cb_result):
                                await cb_result
                        except ArkiBaseError as e:
                            logger.warning("Callback error: %s", e)

                except asyncio.TimeoutError:
                    item.error = "timeout"
                    item.status = "timeout"
                    if item.retries < item.max_retries:
                        item.retries += 1
                        item.priority = max(0, item.priority - 1)
                        self._stats["retried"] += 1
                        await self._queue.put(item)
                    else:
                        item.status = "failed"
                        self._stats["failed"] += 1

                except ArkiBaseError as e:
                    item.error = str(e)
                    if item.retries < item.max_retries:
                        item.retries += 1
                        self._stats["retried"] += 1
                        await asyncio.sleep(0.5 * item.retries)
                        await self._queue.put(item)
                    else:
                        item.status = "failed"
                        self._stats["failed"] += 1
                        logger.error("Queue item %s failed: %s", item.item_id, e)

                self._results[item.item_id] = item

            self._queue.task_done()

    async def start(self, num_workers: int = 3) -> None:
        """Start queue workers."""
        self._running = True
        for i in range(num_workers):
            task = asyncio.create_task(self._worker(i))
            self._workers.append(task)
        logger.info("RequestQueue started with %d workers", num_workers)

    async def stop(self) -> None:
        self._running = False
        for task in self._workers:
            task.cancel()
        self._workers.clear()

    def get_result(self, item_id: str) -> Optional[QueueItem]:
        return self._results.get(item_id)

    @property
    def pending(self) -> int:
        return self._queue.qsize()

    @property
    def stats(self) -> Dict[str, Any]:
        return {**self._stats, "pending": self.pending,
                "workers": len(self._workers)}

    async def cleanup_old_results(self, max_age_s: float = 3600) -> int:
        cutoff = time.time() - max_age_s
        old = [k for k, v in self._results.items() if v.completed_at and v.completed_at < cutoff]
        for k in old:
            del self._results[k]
        # Clean old dedup keys
        old_keys = [k for k, t in self._recent_keys.items() if t < cutoff]
        for k in old_keys:
            del self._recent_keys[k]
        return len(old)

# Singleton
_queue: Optional[RequestQueue] = None
def get_request_queue() -> RequestQueue:
    global _queue
    if _queue is None:
        _queue = RequestQueue()
    return _queue


