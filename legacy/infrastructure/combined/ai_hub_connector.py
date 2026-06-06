
from __future__ import annotations
"""AIHubConnector — Combines AI hub + auto-connector."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)



class AIHubConnector:
    """AIHubConnector — Combines AI hub + auto-connector."""

    def __init__(self, *, name: str = "ai_hub_connector") -> None:
        self.name = name
        self._components: Dict[str, Any] = {}
        self._pipeline: List = []
        self._stats = {"processed": 0, "errors": 0, "total_ms": 0.0}
        logger.info("AIHubConnector '%s' initialized", name)

    def add_component(self, name: str, component: Any) -> None:
        self._components[name] = component

    def set_pipeline(self, steps: List) -> None:
        self._pipeline = steps

    async def process(self, data: Any = None, *, context: Optional[Dict] = None) -> Dict:
        """Process data through the combined pipeline."""
        t0 = time.monotonic()
        self._stats["processed"] += 1
        result = data
        ctx = dict(context or {})

        try:
            for step in self._pipeline:
                if asyncio.iscoroutinefunction(step):
                    result = await step(result, ctx)
                elif callable(step):
                    result = step(result, ctx)
            elapsed = (time.monotonic() - t0) * 1000
            self._stats["total_ms"] += elapsed
            return {"ok": True, "result": result, "ms": round(elapsed, 2)}
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("AIHubConnector error: %s", e)
            return {"ok": False, "error": str(e)}

    def get_component(self, name: str) -> Optional[Any]:
        return self._components.get(name)

    def list_components(self) -> List[str]:
        return sorted(self._components.keys())

    def get_stats(self) -> dict:
        avg = (self._stats["total_ms"] / self._stats["processed"]) if self._stats["processed"] else 0
        return {**self._stats, "avg_ms": round(avg, 2), "components": len(self._components)}


