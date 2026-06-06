
from __future__ import annotations
"""EndpointNode — API endpoint node for request handling."""
import logging
from typing import Any, Callable, Dict, List



logger = logging.getLogger(__name__)


class EndpointNode:
    """Represents an API endpoint in the infrastructure."""

    def __init__(self, path: str = "/", method: str = "POST") -> None:
        self.path = path
        self.method = method
        self._handlers: List[Callable] = []
        self._request_count = 0

    def add_handler(self, handler: Callable) -> None:
        self._handlers.append(handler)

    async def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        self._request_count += 1
        result = request
        for handler in self._handlers:
            try:
                result = await handler(result) if callable(handler) else result
            except Exception as e:
                logger.error("Endpoint %s handler error: %s", self.path, e)
                return {"error": str(e), "status": 500}
        return result

    def stats(self) -> Dict[str, Any]:
        return {"path": self.path, "method": self.method,
                "handlers": len(self._handlers), "requests": self._request_count}


