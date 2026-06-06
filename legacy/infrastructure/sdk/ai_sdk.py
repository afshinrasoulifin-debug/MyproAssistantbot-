
from __future__ import annotations
"""
AISDK — Developer SDK for building AI-powered features.
"""
import logging
from typing import Any, Callable, Dict, List



logger = logging.getLogger(__name__)

class AISDK:
    """High-level SDK for developers to add AI capabilities."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Callable] = {}
        self._middleware: List[Callable] = []

    def on(self, event: str, handler: Callable) -> Any:
        self._handlers[event] = handler

    def use(self, middleware: Callable) -> Any:
        self._middleware.append(middleware)

    async def trigger(self, event: str, data: Any = None) -> Any:
        handler = self._handlers.get(event)
        if handler:
            return await handler(data)
        return None


