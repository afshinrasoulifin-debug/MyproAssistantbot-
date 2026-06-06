
from __future__ import annotations
"""
architecture.service.maintenance — MaintenanceService, RecoveryService
═══════════════════════════════════════════════════════════════════════
System maintenance, cleanup, and recovery operations.
Covers: maintenance, maintenance-service, recovery, recovery-service, maintenance-agent
"""
import asyncio, gc, logging, time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional



logger = logging.getLogger(__name__)

@dataclass
class MaintenanceTask:
    name: str
    action: Callable
    schedule: str = "daily"
    last_run: float = 0
    enabled: bool = True

class MaintenanceService:
    """Periodic maintenance: cleanup, optimization, health checks."""
    def __init__(self) -> None:
        self._tasks: List[MaintenanceTask] = []
        self._log: List[Dict[str, Any]] = []

    def register(self, name: str, action: Callable, schedule: str = "daily") -> None:
        self._tasks.append(MaintenanceTask(name=name, action=action, schedule=schedule))

    async def run_all(self) -> Dict[str, Any]:
        results = {}
        for task in self._tasks:
            if not task.enabled:
                continue
            t0 = time.time()
            try:
                result = task.action()
                if asyncio.iscoroutine(result):
                    result = await result
                task.last_run = time.time()
                results[task.name] = {"status": "ok", "duration_s": round(time.time()-t0, 3)}
            except Exception as exc:
                results[task.name] = {"status": "error", "error": str(exc)}
        self._log.append({"time": time.time(), "results": results})
        return results

    def cleanup_memory(self) -> Dict[str, Any]:
        collected = gc.collect()
        return {"gc_collected": collected}

    @property
    def stats(self) -> Dict[str, Any]:
        return {"tasks": len(self._tasks), "runs": len(self._log)}

class RecoveryService:
    """Error recovery with checkpoint/restore support."""
    def __init__(self) -> None:
        self._checkpoints: Dict[str, Dict[str, Any]] = {}
        self._recovery_handlers: Dict[str, Callable] = {}

    def checkpoint(self, name: str, state: Dict[str, Any]) -> None:
        self._checkpoints[name] = {"state": state, "time": time.time()}

    def restore(self, name: str) -> Optional[Dict[str, Any]]:
        cp = self._checkpoints.get(name)
        if cp:
            return cp["state"]
        return None

    def register_handler(self, error_type: str, handler: Callable) -> None:
        self._recovery_handlers[error_type] = handler

    async def recover(self, error_type: str, context: Dict[str, Any]) -> Any:
        handler = self._recovery_handlers.get(error_type)
        if handler:
            result = handler(context)
            if asyncio.iscoroutine(result):
                result = await result
            return result
        return None


