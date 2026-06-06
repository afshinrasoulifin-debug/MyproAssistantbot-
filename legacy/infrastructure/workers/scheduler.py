
from __future__ import annotations
"""InfraScheduler — Cron-like task scheduling."""
import asyncio, logging
from typing import Callable, Dict, Any



logger = logging.getLogger(__name__)

class InfraScheduler:
    """Schedule periodic tasks."""

    def __init__(self) -> None:
        self._jobs: Dict[str, dict] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    def every(self, name: str, interval: float, fn: Callable) -> Any:
        self._jobs[name] = {"interval": interval, "fn": fn}

    async def start(self) -> Any:
        for name, job in self._jobs.items():
            self._tasks[name] = asyncio.create_task(self._run_job(name, job))

    async def _run_job(self, name: str, job: dict) -> Any:
        while True:
            try:
                await job["fn"]()
            except Exception as e:
                logger.error("Scheduler: %s failed: %s", name, e)
            await asyncio.sleep(job["interval"])


