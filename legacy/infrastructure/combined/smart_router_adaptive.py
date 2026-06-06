
from __future__ import annotations
"""
SmartRouterAdaptive — Combines smart routing + adaptive learning.
"""
import logging, time
from collections import defaultdict
from typing import Any, Callable, Dict



logger = logging.getLogger(__name__)

class SmartRouterAdaptive:
    """Router that learns and adapts routing decisions over time."""

    def __init__(self) -> None:
        self._routes: Dict[str, Callable] = {}
        self._performance: Dict[str, list] = defaultdict(list)
        self._weights: Dict[str, float] = {}

    def add_route(self, name: str, handler: Callable, initial_weight: float = 1.0) -> None:
        self._routes[name] = handler
        self._weights[name] = initial_weight

    async def route(self, request: dict) -> Any:
        best_route = max(self._weights, key=self._weights.get) if self._weights else None
        if not best_route or best_route not in self._routes:
            return {"error": "No routes available"}

        t0 = time.time()
        try:
            result = await self._routes[best_route](request)
            latency = time.time() - t0
            self._performance[best_route].append({"latency": latency, "success": True})
            self._weights[best_route] = min(self._weights[best_route] * 1.02, 10.0)
            return result
        except Exception as e:
            self._weights[best_route] = max(self._weights[best_route] * 0.8, 0.1)
            return {"error": str(e)}


