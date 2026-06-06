
from __future__ import annotations
"""
SmartProxyFallback — Combines smart proxy + fallback chain.
Proxy with automatic failover to backup endpoints.
"""
import logging
from typing import Callable, Dict, List



logger = logging.getLogger(__name__)

class SmartProxyFallback:
    """Smart proxy that falls back through multiple endpoints on failure."""

    def __init__(self) -> None:
        self._endpoints: List[Dict] = []
        self._active_idx = 0
        self._failure_counts: Dict[str, int] = {}

    def add_endpoint(self, name: str, handler: Callable, priority: int = 0) -> None:
        self._endpoints.append({"name": name, "handler": handler, "priority": priority})
        self._endpoints.sort(key=lambda e: -e["priority"])

    async def proxy(self, request: dict) -> dict:
        for endpoint in self._endpoints:
            name = endpoint["name"]
            failures = self._failure_counts.get(name, 0)
            if failures > 10:
                continue  # Skip heavily failed endpoints
            try:
                result = await endpoint["handler"](request)
                self._failure_counts[name] = 0
                return result
            except Exception:
                self._failure_counts[name] = failures + 1
                logger.warning("SmartProxyFallback: %s failed (%d), trying next", name, failures + 1)
        return {"error": "All endpoints exhausted"}


