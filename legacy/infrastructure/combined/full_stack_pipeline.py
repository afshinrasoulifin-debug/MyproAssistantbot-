
from __future__ import annotations
"""
FullStackPipeline — Complete request processing pipeline combining ALL layers.
"""
import asyncio, logging, time
from typing import Any, Callable, Dict, List



logger = logging.getLogger(__name__)

class PipelineStage:
    def __init__(self, name: str, handler: Callable, timeout: float = 60.0) -> None:
        self.name = name
        self.handler = handler
        self.timeout = timeout

class FullStackPipeline:
    """Complete pipeline: intercept → authenticate → route → process → cache → respond."""

    def __init__(self) -> None:
        self._stages: List[PipelineStage] = []
        self._error_handler: Callable = None
        self._metrics = {"processed": 0, "errors": 0, "total_latency": 0.0}

    def add_stage(self, name: str, handler: Callable, timeout: float = 60.0) -> None:
        self._stages.append(PipelineStage(name, handler, timeout))

    def on_error(self, handler: Callable) -> None:
        self._error_handler = handler

    async def process(self, request: Any) -> Any:
        t0 = time.time()
        self._metrics["processed"] += 1
        result = request

        for stage in self._stages:
            try:
                if asyncio.iscoroutinefunction(stage.handler):
                    result = await asyncio.wait_for(stage.handler(result), timeout=stage.timeout)
                else:
                    result = stage.handler(result)
            except Exception as e:
                self._metrics["errors"] += 1
                logger.error("Pipeline stage %s failed: %s", stage.name, e)
                if self._error_handler:
                    return self._error_handler(stage.name, e, request)
                raise

        self._metrics["total_latency"] += time.time() - t0
        return result

    @property
    def stats(self) -> Dict:
        return dict(self._metrics)


