
from __future__ import annotations
"""InternalBus — Internal message bus for inter-component communication."""
import asyncio, logging
from collections import defaultdict
from typing import Any, Callable, Dict, List



logger = logging.getLogger(__name__)

class InternalBus:
    """High-performance internal message bus."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._message_count = 0

    def on(self, event: str, handler: Callable) -> Any:
        self._handlers[event].append(handler)

    def off(self, event: str, handler: Callable) -> Any:
        if handler in self._handlers.get(event, []):
            self._handlers[event].remove(handler)

    async def emit(self, event: str, data: Any = None) -> Any:
        self._message_count += 1
        for handler in self._handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error("Bus event %s handler error: %s", event, e)

    async def emit_all(self, event: str, data: Any = None) -> None:
        await self.emit(event, data)
        await self.emit("*", {"event": event, "data": data})


