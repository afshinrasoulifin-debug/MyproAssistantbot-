
from __future__ import annotations
"""SmartRouter — AI-powered request routing."""
import logging, re
from typing import Any, Callable, Dict, List



logger = logging.getLogger(__name__)

class SmartRouter:
    """Route requests based on content analysis, user history, and model availability."""

    def __init__(self) -> None:
        self._routes: List[Dict] = []
        self._default_handler = None
        self._route_history: list = []

    def add_route(self, pattern: str, handler: Callable, priority: int = 0) -> None:
        self._routes.append({"pattern": pattern, "handler": handler, "priority": priority})
        self._routes.sort(key=lambda r: -r["priority"])

    def set_default(self, handler: Callable) -> None:
        self._default_handler = handler

    async def route(self, request: dict) -> Any:
        text = str(request.get("content", ""))
        for route in self._routes:
            if re.search(route["pattern"], text, re.IGNORECASE):
                self._route_history.append(route["pattern"])
                return await route["handler"](request)
        if self._default_handler:
            return await self._default_handler(request)
        return None


