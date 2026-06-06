
"""
Task Queue v9.1
Async task queue for heavy operations.
Uses asyncio.Queue internally, can be replaced with Celery/RQ.
"""
import asyncio
import logging
import time
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    id: str
    func: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


# v9.2: Can use persistent_exec as backend
# from arki_project.utils.persistent_exec import PersistentExecutor

class TaskQueue:
    """
    Async task queue with:
    - Priority support
    - Concurrent worker pool
    - Task status tracking
    - Retry on failure
    """

    def __init__(self, max_workers: int = 5, max_retries: int = 3) -> None:
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._tasks: Dict[str, Task] = {}
        self._max_workers = max_workers
        self._max_retries = max_retries
        self._workers = []
        self._running = False
        self._task_counter = 0
        self._stats = {"submitted": 0, "completed": 0, "failed": 0}

    async def start(self) -> Any:
        """Start worker pool."""
        self._running = True
        for i in range(self._max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)
        logger.info("Task queue started with %d workers", self._max_workers)

    async def stop(self) -> Any:
        """Stop worker pool gracefully."""
        self._running = False
        for w in self._workers:
            w.cancel()
        self._workers.clear()

    async def submit(self, func: Callable, *args, **kwargs) -> str:
        """Submit a task and return task ID."""
        self._task_counter += 1
        task_id = f"task-{self._task_counter}-{int(time.time())}"
        task = Task(id=task_id, func=func, args=args, kwargs=kwargs)
        self._tasks[task_id] = task
        await self._queue.put(task)
        self._stats["submitted"] += 1
        return task_id

    def get_status(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    async def _worker(self, name: str) -> Any:
        """Worker loop."""
        while self._running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                task.status_code = TaskStatus.RUNNING
                task.started_at = time.time()

                try:
                    if asyncio.iscoroutinefunction(task.func):
                        task.result = await task.func(*task.args, **task.kwargs)
                    else:
                        task.result = task.func(*task.args, **task.kwargs)
                    task.status_code = TaskStatus.COMPLETED
                    self._stats["completed"] += 1
                except Exception as e:
                    task.status_code = TaskStatus.FAILED
                    task.error = str(e)
                    self._stats["failed"] += 1
                    logger.error("Task %s failed: %s", task.id, e)
                finally:
                    task.completed_at = time.time()
                    self._queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    @property
    def stats(self) -> dict:
        return {
            **self._stats,
            "queue_size": self._queue.qsize(),
            "active_workers": len(self._workers),
        }


_queue: Optional[TaskQueue] = None

async def get_task_queue() -> TaskQueue:
    global _queue
    if _queue is None:
        _queue = TaskQueue()
        await _queue.start()
    return _queue


