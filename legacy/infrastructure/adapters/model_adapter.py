
from __future__ import annotations
"""ModelAdapter — Adapt model-specific formats."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)



class ModelAdapter:
    """ModelAdapter — Adapt model-specific formats."""

    def __init__(self, client: Any = None, *, config: Optional[Dict] = None) -> None:
        self._client = client
        self._config = config or {}
        self._transforms: List = []
        self._stats = {"adapted": 0, "errors": 0, "total_ms": 0.0}
        logger.info("ModelAdapter initialized (config=%d keys)", len(self._config))

    def add_transform(self, fn: Any) -> "ModelAdapter":
        """Register a transform function."""
        self._transforms.append(fn)
        return self

    async def adapt_request(self, request: dict) -> dict:
        """Transform an incoming request through the adapter pipeline."""
        t0 = time.monotonic()
        result = dict(request)
        for fn in self._transforms:
            try:
                if asyncio.iscoroutinefunction(fn):
                    result = await fn(result)
                else:
                    result = fn(result)
            except Exception as e:
                self._stats["errors"] += 1
                logger.warning("ModelAdapter transform error: %s", e)
        elapsed = (time.monotonic() - t0) * 1000
        self._stats["adapted"] += 1
        self._stats["total_ms"] += elapsed
        return result

    async def adapt_response(self, response: dict) -> dict:
        """Transform an outgoing response through the adapter pipeline."""
        result = dict(response)
        result.setdefault("_adapter", "ModelAdapter")
        result.setdefault("_adapted_at", time.time())
        return result

    def get_stats(self) -> dict:
        """Return adapter performance stats."""
        avg = (self._stats["total_ms"] / self._stats["adapted"]) if self._stats["adapted"] else 0
        return {**self._stats, "avg_ms": round(avg, 2)}

    def reset(self) -> None:
        """Reset adapter state."""
        self._transforms.clear()
        self._stats = {"adapted": 0, "errors": 0, "total_ms": 0.0}


