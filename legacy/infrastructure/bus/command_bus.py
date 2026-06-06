
from __future__ import annotations
"""InfraCommandBus — Command dispatch bus."""

import asyncio
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)



class InfraCommandBus:
    """InfraCommandBus — Command dispatch bus."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List] = {}
        self._queue: List[Dict] = []
        self._stats = {"published": 0, "handled": 0, "errors": 0}
        logger.info("InfraCommandBus initialized")

    def subscribe(self, event_type: str, handler: Any) -> None:
        """Subscribe a handler to an event type."""
        self._handlers.setdefault(event_type, []).append(handler)
        logger.debug("Subscribed to '%s' (%d handlers)", event_type, len(self._handlers[event_type]))

    def unsubscribe(self, event_type: str, handler: Any) -> bool:
        """Remove a handler from an event type."""
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            return True
        return False

    async def publish(self, event_type: str, data: Any = None) -> int:
        """Publish an event to all subscribers."""
        self._stats["published"] += 1
        handlers = self._handlers.get(event_type, [])
        handled = 0

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
                handled += 1
                self._stats["handled"] += 1
            except Exception as e:
                self._stats["errors"] += 1
                logger.warning("InfraCommandBus handler error for '%s': %s", event_type, e)

        return handled

    async def publish_batch(self, events: List[Dict]) -> int:
        """Publish multiple events."""
        total = 0
        for ev in events:
            total += await self.publish(ev.get("type", "unknown"), ev.get("data"))
        return total

    @property
    def event_types(self) -> List[str]:
        return list(self._handlers.keys())

    def get_stats(self) -> dict:
        return {**self._stats, "event_types": len(self._handlers)}


