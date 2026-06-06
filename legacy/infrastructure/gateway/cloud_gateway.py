
from __future__ import annotations
"""CloudGateway — Multi-cloud AI gateway."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)



class CloudGateway:
    """CloudGateway — Multi-cloud AI gateway."""

    def __init__(self, *, name: str = "cloud_gateway") -> None:
        self.name = name
        self._routes: Dict[str, Any] = {}
        self._middleware: List = []
        self._rate_limits: Dict[str, float] = {}
        self._stats = {"routed": 0, "rejected": 0, "errors": 0}
        logger.info("CloudGateway '%s' initialized", name)

    def add_route(self, path: str, target: Any, *, rate_limit: float = 0) -> None:
        """Add a gateway route."""
        self._routes[path] = target
        if rate_limit > 0:
            self._rate_limits[path] = rate_limit

    def add_middleware(self, fn: Any) -> None:
        self._middleware.append(fn)

    async def route(self, path: str, request: Optional[Dict] = None) -> Dict:
        """Route a request through the gateway."""
        if path not in self._routes:
            self._stats["rejected"] += 1
            return {"status": 404, "error": f"No route: {path}"}

        # Rate limit check
        if path in self._rate_limits:
            limit = self._rate_limits[path]
            if self._stats["routed"] > limit:
                self._stats["rejected"] += 1
                return {"status": 429, "error": "Rate limited"}

        self._stats["routed"] += 1
        req = dict(request or {})

        # Apply middleware
        for mw in self._middleware:
            try:
                if asyncio.iscoroutinefunction(mw):
                    req = await mw(req)
                else:
                    req = mw(req)
            except Exception as e:
                self._stats["errors"] += 1
                return {"status": 500, "error": f"Middleware error: {e}"}

        target = self._routes[path]
        try:
            if callable(target):
                if asyncio.iscoroutinefunction(target):
                    result = await target(req)
                else:
                    result = target(req)
                return {"status": 200, "data": result}
            return {"status": 200, "target": str(target)}
        except Exception as e:
            self._stats["errors"] += 1
            return {"status": 500, "error": str(e)}

    def list_routes(self) -> List[str]:
        return sorted(self._routes.keys())

    def get_stats(self) -> dict:
        return {**self._stats, "routes": len(self._routes)}


