
from __future__ import annotations
"""AIRelay — Relay AI requests between providers."""
import logging
from typing import Callable, Dict



logger = logging.getLogger(__name__)

class AIRelay:
    """Relay requests from one provider to another with transformation."""

    def __init__(self) -> None:
        self._routes: Dict[str, str] = {}
        self._transforms: Dict[str, Callable] = {}

    def add_route(self, source: str, target: str, transform: Callable = None) -> None:
        self._routes[source] = target
        if transform:
            self._transforms[source] = transform

    async def relay(self, source: str, request: dict) -> dict:
        target = self._routes.get(source)
        if not target:
            return {"error": f"No relay route for {source}"}
        transform = self._transforms.get(source)
        if transform:
            request = transform(request)
        return {"relayed_to": target, "request": request}


