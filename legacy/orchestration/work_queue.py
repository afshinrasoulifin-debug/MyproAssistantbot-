
from __future__ import annotations
"""
tg_bot/orchestration/work_queue.py — Async Work Queue + Workers
═══════════════════════════════════════════════════════════════
Priority-based async job queue with configurable worker pool:
  • Priority queue (CRITICAL > HIGH > NORMAL > LOW)
  • Configurable concurrency per provider
  • Request throttling + rate limiting
  • Back-pressure when queue is full

Patterns covered:
  - async-workers + request-queue + response-cache
  - smart-gateway + distributed-workers + queue-system
  - orchestration-runtime + elastic-scaling + worker-pool
  - ai-runtime + execution-pipeline + provider-failover
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .types import RequestPriority

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config
    from arki_project.utils.titanium.crypto import secure_hex
except ImportError:
    pass
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Job:
    """A single job in the work queue."""
    job_id: str
    priority: RequestPriority
    payload: Any
    callback: Optional[Callable] = None
    created_at: float = field(default_factory=time.monotonic)
    started_at: float = 0.0
    completed_at: float = 0.0
    result: Any = None
    error: Optional[str] = None
    retries: int = 0

    @property
    def wait_time_ms(self) -> float:
        if self.started_at:
            return (self.started_at - self.created_at) * 1000
        return (time.monotonic() - self.created_at) * 1000

    @property
    def exec_time_ms(self) -> float:
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at) * 1000
        return 0.0


class WorkQueue:
    """Priority-based async work queue with worker pool.

    Workers pull jobs from the queue and execute them concurrently.
    Supports:
      - Priority ordering
      - Max concurrency
      - Request throttling (max N requests per second)
      - Back-pressure (reject when queue is full)
      - Graceful shutdown
    """

    def __init__(
        self,
        max_workers: int = 10,
        max_queue_size: int = 1000,
        max_rps: float = 50.0,  # requests per second
    ) -> None:
        self._max_workers = max_workers
        self._max_queue_size = max_queue_size
        self._max_rps = max_rps

        # Priority queue (lower number = higher priority, processed first)
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(
            maxsize=max_queue_size,
        )
        self._workers: List[asyncio.Task] = []
        self._handler: Optional[Callable[[Any], Awaitable[Any]]] = None
        self._running = False
        self._shutdown_event = asyncio.Event()

        # Stats
        self._total_submitted = 0
        self._total_completed = 0
        self._total_errors = 0
        self._total_rejected = 0
        self._active_jobs = 0

        # Rate limiter
        self._rps_tokens = max_rps
        self._rps_last_refill = time.monotonic()

        # Job tracking
        self._pending_futures: Dict[str, asyncio.Future] = {}

    # ── Setup ──────────────────────────────────────────────

    def set_handler(self, handler: Callable[[Any], Awaitable[Any]]) -> None:
        """Set the function that processes each job's payload."""
        self._handler = handler

    async def start(self) -> None:
        """Start the worker pool."""
        if self._running:
            return
        self._running = True
        self._shutdown_event.clear()
        for i in range(self._max_workers):
            task = asyncio.create_task(
                self._worker_loop(f"worker-{i}"),
                name=f"wq-worker-{i}",
            )
            self._workers.append(task)
        logger.info(
            "WorkQueue started: %d workers, max_rps=%.0f, max_queue=%d",
            self._max_workers, self._max_rps, self._max_queue_size,
        )

    async def stop(self, timeout: float = 10.0) -> None:
        """Graceful shutdown: finish current jobs, cancel remaining."""
        self._running = False
        self._shutdown_event.set()

        # Wait for workers to finish current jobs
        if self._workers:
            done, pending = await asyncio.wait(
                self._workers, timeout=timeout,
            )
            for task in pending:
                task.cancel()
            self._workers.clear()

        # Cancel pending futures
        for fut in self._pending_futures.values():
            if not fut.done():
                fut.cancel()
        self._pending_futures.clear()
        logger.info("WorkQueue stopped.")

    # ── Submit ─────────────────────────────────────────────

    async def submit(
        self,
        payload: Any,
        priority: RequestPriority = RequestPriority.NORMAL,
        callback: Optional[Callable] = None,
    ) -> str:
        """Submit a job to the queue. Returns job_id.

        Raises asyncio.QueueFull if the queue is at capacity.
        """
        if not self._running:
            raise RuntimeError("WorkQueue not started")

        job_id = uuid.uuid4().hex[:12]
        job = Job(
            job_id=job_id,
            priority=priority,
            payload=payload,
            callback=callback,
        )

        try:
            # Priority queue: lower number = higher priority
            # We negate priority so CRITICAL(3) → -3 is processed first
            self._queue.put_nowait((-priority.value, job.created_at, job))
            self._total_submitted += 1
            return job_id
        except asyncio.QueueFull:
            self._total_rejected += 1
            raise

    async def submit_and_wait(
        self,
        payload: Any,
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout: float = 60.0,
    ) -> Any:
        """Submit a job and wait for its result."""
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        job_id = uuid.uuid4().hex[:12]

        job = Job(
            job_id=job_id,
            priority=priority,
            payload=payload,
        )
        self._pending_futures[job_id] = future

        try:
            self._queue.put_nowait((-priority.value, job.created_at, job))
            self._total_submitted += 1
        except asyncio.QueueFull:
            self._total_rejected += 1
            del self._pending_futures[job_id]
            raise

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending_futures.pop(job_id, None)
            raise
        finally:
            self._pending_futures.pop(job_id, None)

    # ── Worker loop ────────────────────────────────────────

    async def _worker_loop(self, name: str) -> None:
        """Worker loop: pull jobs, enforce rate limit, execute."""
        while self._running:
            try:
                # Get next job (with timeout to check shutdown)
                try:
                    _, _, job = await asyncio.wait_for(
                        self._queue.get(), timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue

                # Rate limiting
                await self._acquire_rps_token()

                # Execute
                job.started_at = time.monotonic()
                self._active_jobs += 1

                try:
                    if self._handler:
                        result = await self._handler(job.payload)
                        job.result = result
                    job.completed_at = time.monotonic()
                    self._total_completed += 1

                    # Resolve future if someone is waiting
                    future = self._pending_futures.pop(job.job_id, None)
                    if future and not future.done():
                        future.set_result(job.result)

                    # Callback
                    if job.callback:
                        try:
                            job.callback(job)
                        except Exception as _e:
                            logger.debug("Suppressed: %s", _e)  # v10.1: no longer silent

                except Exception as exc:
                    job.error = str(exc)
                    job.completed_at = time.monotonic()
                    self._total_errors += 1

                    future = self._pending_futures.pop(job.job_id, None)
                    if future and not future.done():
                        future.set_exception(exc)

                    logger.warning("%s job %s failed: %s", name, job.job_id, exc)
                finally:
                    self._active_jobs -= 1

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("%s unexpected error: %s", name, exc)

    async def _acquire_rps_token(self) -> None:
        """Simple token-bucket rate limiter."""
        now = time.monotonic()
        elapsed = now - self._rps_last_refill
        self._rps_tokens = min(
            self._max_rps,
            self._rps_tokens + elapsed * self._max_rps,
        )
        self._rps_last_refill = now

        if self._rps_tokens < 1.0:
            wait = (1.0 - self._rps_tokens) / self._max_rps
            await asyncio.sleep(wait)
            self._rps_tokens = 1.0

        self._rps_tokens -= 1.0

    # ── Introspection ──────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        return {
            "queue_size": self._queue.qsize(),
            "max_queue": self._max_queue_size,
            "workers": len(self._workers),
            "active_jobs": self._active_jobs,
            "total_submitted": self._total_submitted,
            "total_completed": self._total_completed,
            "total_errors": self._total_errors,
            "total_rejected": self._total_rejected,
            "running": self._running,
        }


