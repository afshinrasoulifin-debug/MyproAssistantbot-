
from __future__ import annotations
"""OptimizationEngine — Request and response optimization."""

import asyncio
import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)



class OptimizationEngine:
    """OptimizationEngine — Request and response optimization."""

    def __init__(self, *, name: str = "optimization_engine") -> None:
        self.name = name
        self._pipelines: Dict[str, List] = {}
        self._cache: Dict[str, Any] = {}
        self._stats = {"runs": 0, "cache_hits": 0, "errors": 0, "total_ms": 0.0}
        logger.info("OptimizationEngine '%s' initialized", name)

    def define_pipeline(self, name: str, steps: List) -> None:
        """Define a processing pipeline."""
        self._pipelines[name] = steps
        logger.debug("Pipeline '%s' defined with %d steps", name, len(steps))

    async def run(self, pipeline: str, input_data: Any = None, *, use_cache: bool = True) -> Dict:
        """Execute a named pipeline."""
        cache_key = f"{pipeline}:{hash(str(input_data))}"
        if use_cache and cache_key in self._cache:
            self._stats["cache_hits"] += 1
            return {"ok": True, "cached": True, "result": self._cache[cache_key]}

        steps = self._pipelines.get(pipeline, [])
        if not steps:
            return {"ok": False, "error": f"Unknown pipeline: {pipeline}"}

        self._stats["runs"] += 1
        t0 = time.monotonic()
        result = input_data

        try:
            for i, step in enumerate(steps):
                if asyncio.iscoroutinefunction(step):
                    result = await step(result)
                elif callable(step):
                    result = step(result)
            elapsed = (time.monotonic() - t0) * 1000
            self._stats["total_ms"] += elapsed

            if use_cache:
                self._cache[cache_key] = result
            return {"ok": True, "result": result, "steps": len(steps), "ms": round(elapsed, 2)}
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("OptimizationEngine pipeline '%s' error: %s", pipeline, e)
            return {"ok": False, "error": str(e)}

    def clear_cache(self) -> int:
        """Clear engine cache."""
        count = len(self._cache)
        self._cache.clear()
        return count

    def get_stats(self) -> dict:
        return {**self._stats, "pipelines": len(self._pipelines), "cache_size": len(self._cache)}


