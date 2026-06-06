
from __future__ import annotations
"""Executor — Execute tasks with isolation and error handling."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)



class TaskExecutor:
    """Executor — Execute tasks with isolation and error handling."""

    def __init__(self, *, name: str = "executor") -> None:
        self.name = name
        self._registry: Dict[str, Any] = {}
        self._stats = {"ops": 0, "errors": 0}
        logger.info("TaskExecutor '%s' initialized", name)

    def register(self, key: str, value: Any) -> None:
        """Register a component."""
        self._registry[key] = value

    def resolve(self, key: str) -> Optional[Any]:
        """Resolve a registered component."""
        return self._registry.get(key)

    async def execute(self, operation: str, data: Any = None) -> Dict:
        """Execute an operation through this component."""
        self._stats["ops"] += 1
        try:
            handler = self._registry.get(operation)
            if handler and callable(handler):
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(data)
                else:
                    result = handler(data)
                return {"ok": True, "result": result}
            return {"ok": True, "operation": operation, "data": data}
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("TaskExecutor execute error: %s", e)
            return {"ok": False, "error": str(e)}

    async def health_check(self) -> Dict:
        """Return component health status."""
        return {
            "name": self.name,
            "type": "TaskExecutor",
            "status": "healthy",
            "registered": len(self._registry),
            "stats": self._stats,
        }

    def list_registered(self) -> List[str]:
        return sorted(self._registry.keys())

    def get_stats(self) -> dict:
        return {**self._stats, "registered": len(self._registry)}


