
from __future__ import annotations
"""
WorkflowEngineScheduler — Combines workflow engine + scheduler.
"""
import asyncio, logging
from typing import Callable, Dict, List, Any, Optional



logger = logging.getLogger(__name__)

class WorkflowEngineScheduler:
    """Scheduled workflow execution."""

    def __init__(self) -> None:
        self._workflows: Dict[str, List[Callable]] = {}
        self._schedules: Dict[str, float] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    def define(self, name: str, steps: List[Callable]) -> Any:
        self._workflows[name] = steps

    def schedule(self, name: str, interval: float) -> Any:
        self._schedules[name] = interval

    async def start_all(self) -> None:
        for name, interval in self._schedules.items():
            self._tasks[name] = asyncio.create_task(self._run_loop(name, interval))

    async def _run_loop(self, name: str, interval: float) -> Any:
        while True:
            await self.run(name)
            await asyncio.sleep(interval)

    async def run(self, name: str, input_data: Optional[Any]=None) -> Any:
        steps = self._workflows.get(name, [])
        result = input_data
        for step in steps:
            result = await step(result) if asyncio.iscoroutinefunction(step) else step(result)
        return result


