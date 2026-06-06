
from __future__ import annotations
"""InfraTaskRunner — Named task execution with timeout and retry."""
import asyncio, logging, time
from typing import Any, Callable, Dict



logger = logging.getLogger(__name__)

class InfraTaskRunner:
    """Run named tasks with timeout, retry, and result tracking."""

    def __init__(self) -> None:
        self._results: Dict[str, Any] = {}
        self._running: Dict[str, bool] = {}

    async def run(self, name: str, fn: Callable, *args, timeout: float = 300, retries: int = 3) -> Any:
        self._running[name] = True
        try:
            for attempt in range(retries):
                try:
                    result = await asyncio.wait_for(fn(*args), timeout=timeout)
                    self._results[name] = {"result": result, "time": time.time(), "attempts": attempt + 1}
                    return result
                except asyncio.TimeoutError:
                    logger.warning("TaskRunner: %s timed out (attempt %d)", name, attempt + 1)
                except Exception as e:
                    logger.error("TaskRunner: %s failed: %s (attempt %d)", name, e, attempt + 1)
                    if attempt == retries - 1:
                        raise
        finally:
            self._running[name] = False


