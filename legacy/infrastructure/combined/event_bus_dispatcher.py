
from __future__ import annotations
"""
EventBusDispatcher — Combines event bus + command dispatcher.
"""
import asyncio, logging
from collections import defaultdict
from typing import Any, Callable, Dict, List



logger = logging.getLogger(__name__)

class EventBusDispatcher:
    """Unified event bus with command dispatching."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._commands: Dict[str, Callable] = {}
        self._event_count = 0

    def on(self, event: str, handler: Callable) -> Any:
        self._subscribers[event].append(handler)

    def command(self, name: str, handler: Callable) -> Any:
        self._commands[name] = handler

    async def emit(self, event: str, data: Any = None) -> Any:
        self._event_count += 1
        for handler in self._subscribers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error("Event handler error: %s: %s", event, e)

    async def dispatch(self, command: str, data: Any = None) -> Any:
        handler = self._commands.get(command)
        if handler:
            return await handler(data) if asyncio.iscoroutinefunction(handler) else handler(data)
        raise ValueError(f"Unknown command: {command}")


