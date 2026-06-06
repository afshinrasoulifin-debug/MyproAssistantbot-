
from __future__ import annotations
"""AINode — Single AI compute node."""

import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)



class AINode:
    """AINode — Single AI compute node."""

    def __init__(self, node_id: str = "ai_node", *, capacity: int = 100) -> None:
        self.node_id = node_id
        self._capacity = capacity
        self._load = 0
        self._tasks: Dict[str, Dict] = {}
        self._status = "ready"
        self._stats = {"executed": 0, "errors": 0, "total_ms": 0.0}
        logger.info("AINode '%s' initialized (cap=%d)", node_id, capacity)

    async def submit(self, task_id: str, payload: Any = None) -> Dict:
        """Submit a task to this node."""
        if self._load >= self._capacity:
            return {"ok": False, "error": "Node at capacity"}

        self._load += 1
        self._tasks[task_id] = {"payload": payload, "submitted_at": time.time(), "status": "queued"}
        return {"ok": True, "task_id": task_id, "node": self.node_id}

    async def execute(self, task_id: str) -> Dict:
        """Execute a submitted task."""
        if task_id not in self._tasks:
            return {"ok": False, "error": f"Task not found: {task_id}"}

        t0 = time.monotonic()
        task = self._tasks[task_id]
        task["status"] = "running"

        try:
            # Actual execution would delegate to registered handlers
            elapsed = (time.monotonic() - t0) * 1000
            task["status"] = "completed"
            self._stats["executed"] += 1
            self._stats["total_ms"] += elapsed
            self._load = max(0, self._load - 1)
            return {"ok": True, "task_id": task_id, "ms": round(elapsed, 2)}
        except Exception as e:
            task["status"] = "failed"
            self._stats["errors"] += 1
            self._load = max(0, self._load - 1)
            return {"ok": False, "error": str(e)}

    @property
    def utilization(self) -> float:
        return (self._load / self._capacity * 100) if self._capacity else 0

    def get_status(self) -> Dict:
        return {
            "node_id": self.node_id,
            "status": self._status,
            "load": self._load,
            "capacity": self._capacity,
            "utilization": f"{self.utilization:.1f}%",
            "stats": self._stats,
        }


