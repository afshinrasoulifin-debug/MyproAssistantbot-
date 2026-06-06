
from __future__ import annotations
"""
EdgeRuntimeProxy — Combines edge runtime + proxy for hybrid inference.
"""
import logging
from typing import Any



logger = logging.getLogger(__name__)

class EdgeRuntimeProxy:
    """Route between local edge inference and cloud proxy."""

    def __init__(self) -> None:
        self._edge = None
        self._cloud = None
        self._prefer_edge = True

    def set_edge(self, runtime: Any) -> None:
        self._edge = runtime

    def set_cloud(self, proxy: Any) -> None:
        self._cloud = proxy

    async def infer(self, request: dict) -> dict:
        if self._prefer_edge and self._edge:
            try:
                return {"source": "edge", "result": await self._edge.local_infer(str(request))}
            except Exception as _exc:
                logger.debug("Suppressed: %s", _exc)
        if self._cloud:
            return {"source": "cloud", "result": await self._cloud.proxy(request, None)}
        return {"error": "No backend"}


