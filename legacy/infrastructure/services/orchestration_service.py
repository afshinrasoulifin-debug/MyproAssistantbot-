
from __future__ import annotations
"""InfraOrchestrationService — Orchestrate complex multi-step operations."""

import asyncio
import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)



class InfraOrchestrationService:
    """InfraOrchestrationService — Orchestrate complex multi-step operations."""

    def __init__(self, *, name: str = "orchestration_service") -> None:
        self.name = name
        self._running = False
        self._handlers: Dict[str, Any] = {}
        self._queue: List[Dict] = []
        self._stats = {"processed": 0, "errors": 0, "total_ms": 0.0}
        logger.info("InfraOrchestrationService '%s' initialized", name)

    async def start(self) -> None:
        self._running = True
        logger.info("InfraOrchestrationService '%s' started", self.name)

    async def stop(self) -> None:
        self._running = False
        logger.info("InfraOrchestrationService '%s' stopped", self.name)

    def register_handler(self, action: str, handler: Any) -> None:
        """Register an action handler."""
        self._handlers[action] = handler

    async def process(self, action: str, data: Any = None) -> Dict:
        """Process an action through the service."""
        if not self._running:
            return {"ok": False, "error": "Service not running"}

        t0 = time.monotonic()
        handler = self._handlers.get(action)

        if not handler:
            return {"ok": False, "error": f"No handler for: {action}"}

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(data)
            else:
                result = handler(data)
            elapsed = (time.monotonic() - t0) * 1000
            self._stats["processed"] += 1
            self._stats["total_ms"] += elapsed
            return {"ok": True, "result": result, "ms": round(elapsed, 2)}
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("InfraOrchestrationService process error: %s", e)
            return {"ok": False, "error": str(e)}

    async def enqueue(self, action: str, data: Any = None) -> int:
        """Queue an action for later processing."""
        self._queue.append({"action": action, "data": data, "queued_at": time.time()})
        return len(self._queue)

    async def flush_queue(self) -> List[Dict]:
        """Process all queued items."""
        results = []
        while self._queue:
            item = self._queue.pop(0)
            result = await self.process(item["action"], item["data"])
            results.append(result)
        return results

    @property
    def is_running(self) -> bool:
        return self._running

    def get_stats(self) -> dict:
        avg = (self._stats["total_ms"] / self._stats["processed"]) if self._stats["processed"] else 0
        return {**self._stats, "avg_ms": round(avg, 2), "queue_size": len(self._queue), "running": self._running}


