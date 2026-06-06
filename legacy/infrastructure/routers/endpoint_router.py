
from __future__ import annotations
"""EndpointRouter — Route to API endpoints."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)



class EndpointRouter:
    """EndpointRouter — Route to API endpoints."""

    def __init__(self, *, default_target: str = "") -> None:
        self._routes: Dict[str, Any] = {}
        self._default = default_target
        self._weights: Dict[str, float] = {}
        self._stats = {"routed": 0, "defaults": 0, "errors": 0}
        logger.info("EndpointRouter initialized")

    def add_route(self, pattern: str, target: Any, *, weight: float = 1.0) -> None:
        """Add a routing rule."""
        self._routes[pattern] = target
        self._weights[pattern] = weight

    def remove_route(self, pattern: str) -> bool:
        if pattern in self._routes:
            del self._routes[pattern]
            self._weights.pop(pattern, None)
            return True
        return False

    async def route(self, key: str, data: Any = None) -> Dict:
        """Route a request to the best matching target."""
        self._stats["routed"] += 1

        # Exact match
        if key in self._routes:
            target = self._routes[key]
            return {"ok": True, "target": str(target), "match": "exact", "key": key}

        # Prefix match (weighted)
        candidates = []
        for pattern, target in self._routes.items():
            if key.startswith(pattern) or pattern == "*":
                candidates.append((pattern, target, self._weights.get(pattern, 1.0)))

        if candidates:
            best = max(candidates, key=lambda x: (len(x[0]), x[2]))
            return {"ok": True, "target": str(best[1]), "match": "prefix", "pattern": best[0]}

        # Default
        if self._default:
            self._stats["defaults"] += 1
            return {"ok": True, "target": self._default, "match": "default"}

        return {"ok": False, "error": f"No route for: {key}"}

    def list_routes(self) -> List[str]:
        return sorted(self._routes.keys())

    def get_stats(self) -> dict:
        return {**self._stats, "routes": len(self._routes)}


