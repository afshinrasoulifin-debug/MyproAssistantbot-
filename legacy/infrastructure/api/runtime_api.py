
from __future__ import annotations
"""RuntimeAPI — Runtime control API."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)



class RuntimeAPI:
    """RuntimeAPI — Runtime control API."""

    def __init__(self, *, prefix: str = "/api") -> None:
        self._prefix = prefix
        self._endpoints: Dict[str, Dict] = {}
        self._middleware: List = []
        self._stats = {"calls": 0, "errors": 0}
        logger.info("RuntimeAPI initialized (prefix=%s)", prefix)

    def register(self, path: str, method: str = "GET", handler: Optional[Any]=None, **meta) -> None:
        """Register an API endpoint."""
        key = f"{method.upper()} {self._prefix}{path}"
        self._endpoints[key] = {
            "path": path,
            "method": method.upper(),
            "handler": handler,
            "meta": meta,
        }
        logger.debug("Registered: %s", key)

    def add_middleware(self, fn: Any) -> None:
        """Add middleware to the API pipeline."""
        self._middleware.append(fn)

    async def handle(self, method: str, path: str, body: Optional[Dict] = None) -> Dict:
        """Route and handle an API request."""
        key = f"{method.upper()} {self._prefix}{path}"
        self._stats["calls"] += 1

        if key not in self._endpoints:
            return {"status": 404, "error": f"Not found: {key}"}

        endpoint = self._endpoints[key]
        request = {"method": method, "path": path, "body": body or {}}

        # Run middleware
        for mw in self._middleware:
            try:
                if asyncio.iscoroutinefunction(mw):
                    request = await mw(request)
                else:
                    request = mw(request)
            except Exception as e:
                self._stats["errors"] += 1
                return {"status": 500, "error": f"Middleware error: {e}"}

        # Execute handler
        handler = endpoint["handler"]
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(request)
                else:
                    result = handler(request)
                return {"status": 200, "data": result}
            except Exception as e:
                self._stats["errors"] += 1
                logger.error("RuntimeAPI handler error: %s", e)
                return {"status": 500, "error": str(e)}

        return {"status": 200, "data": {"endpoint": key, "meta": endpoint["meta"]}}

    def list_endpoints(self) -> List[str]:
        return sorted(self._endpoints.keys())

    def get_stats(self) -> dict:
        return {**self._stats, "endpoints": len(self._endpoints)}


