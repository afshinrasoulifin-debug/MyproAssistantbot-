
from __future__ import annotations
"""
MegaOrchestrator — Master orchestrator combining ALL infrastructure components.
This is the top-level entry point for the entire infrastructure.
"""
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class MegaOrchestrator:
    """Master orchestrator — wires and coordinates ALL infrastructure components.

    Usage:
        orchestrator = MegaOrchestrator()
        await orchestrator.boot()
        result = await orchestrator.process(request)
    """

    def __init__(self) -> None:
        self._registry = None
        self._pipeline = None
        self._event_bus = None
        self._booted = False
        self._stats = {"total_requests": 0, "boot_time": 0}

    def set_registry(self, registry: Any) -> None:
        self._registry = registry

    def set_pipeline(self, pipeline: Any) -> None:
        self._pipeline = pipeline

    def set_event_bus(self, bus: Any) -> None:
        self._event_bus = bus

    async def boot(self) -> Any:
        """Initialize all infrastructure components."""
        import time
        t0 = time.time()
        if self._registry:
            self._registry.auto_register()
        self._booted = True
        self._stats["boot_time"] = time.time() - t0
        logger.info("MegaOrchestrator: booted in %.3fs with %d components",
                    self._stats["boot_time"],
                    self._registry.component_count if self._registry else 0)

    async def process(self, request: Any) -> Any:
        self._stats["total_requests"] += 1
        if self._event_bus:
            await self._event_bus.emit("request:incoming", request)

        if self._pipeline:
            result = await self._pipeline.process(request)
        else:
            result = request

        if self._event_bus:
            await self._event_bus.emit("request:completed", result)
        return result

    @property
    def status(self) -> Dict:
        return {
            "booted": self._booted,
            "components": self._registry.component_count if self._registry else 0,
            **self._stats
        }


