
from __future__ import annotations
"""WebSocketProxy — WebSocket connection proxy."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)



class WebSocketProxy:
    """WebSocketProxy — WebSocket connection proxy."""

    def __init__(self, *, name: str = "websocket_proxy") -> None:
        self.name = name
        self._targets: Dict[str, str] = {}
        self._filters: List = []
        self._stats = {"proxied": 0, "filtered": 0, "errors": 0, "bytes": 0}
        logger.info("WebSocketProxy '%s' initialized", name)

    def add_target(self, name: str, endpoint: str) -> None:
        """Add a proxy target."""
        self._targets[name] = endpoint
        logger.debug("Proxy target: %s -> %s", name, endpoint)

    def add_filter(self, fn: Any) -> None:
        """Add a request filter."""
        self._filters.append(fn)

    async def proxy(self, target: str, request: Dict) -> Dict:
        """Proxy a request to a target."""
        if target not in self._targets:
            return {"status": 404, "error": f"Unknown target: {target}"}

        # Apply filters
        for filt in self._filters:
            try:
                allowed = filt(request) if callable(filt) else True
                if not allowed:
                    self._stats["filtered"] += 1
                    return {"status": 403, "error": "Filtered"}
            except Exception as e:
                logger.warning("WebSocketProxy filter error: %s", e)

        endpoint = self._targets[target]
        self._stats["proxied"] += 1
        size = len(str(request))
        self._stats["bytes"] += size

        return {
            "status": 200,
            "target": target,
            "endpoint": endpoint,
            "proxied": True,
            "size": size,
        }

    async def proxy_broadcast(self, request: Dict) -> Dict[str, Dict]:
        """Proxy to all targets."""
        results = {}
        for target in self._targets:
            results[target] = await self.proxy(target, request)
        return results

    def list_targets(self) -> List[str]:
        return sorted(self._targets.keys())

    def get_stats(self) -> dict:
        return {**self._stats, "targets": len(self._targets)}


