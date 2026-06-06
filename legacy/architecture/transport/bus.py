
from __future__ import annotations
"""
architecture.transport.bus — EventBus, CommandBus, ServiceBus, UtilityBus
═══════════════════════════════════════════════════════════════════════
Publish-subscribe message buses for decoupled communication.
Covers: event-bus, command-bus, service-bus, utility-bus
"""
import asyncio, logging, time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List



logger = logging.getLogger(__name__)

@dataclass
class BusMessage:
    topic: str
    payload: Any
    sender: str = ""
    timestamp: float = field(default_factory=time.time)
    message_id: str = ""

class EventBus:
    """Async publish-subscribe event bus."""
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._message_count = 0
        self._history: List[BusMessage] = []

    def subscribe(self, topic: str, handler: Callable) -> None:
        self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Callable) -> bool:
        subs = self._subscribers.get(topic, [])
        if handler in subs:
            subs.remove(handler)
            return True
        return False

    async def publish(self, topic: str, payload: Any, sender: str = "") -> int:
        msg = BusMessage(topic=topic, payload=payload, sender=sender,
                         message_id=f"msg_{self._message_count}")
        self._message_count += 1
        self._history.append(msg)
        if len(self._history) > 500:
            self._history = self._history[-250:]
        delivered = 0
        for handler in self._subscribers.get(topic, []):
            try:
                result = handler(msg)
                if asyncio.iscoroutine(result):
                    await result
                delivered += 1
            except Exception as exc:
                logger.error("EventBus handler error on %s: %s", topic, exc)
        # Also deliver to wildcard subscribers
        for handler in self._subscribers.get("*", []):
            try:
                result = handler(msg)
                if asyncio.iscoroutine(result):
                    await result
                delivered += 1
            except Exception as exc:
                logger.error("EventBus wildcard handler error: %s", exc)
        return delivered

    @property
    def stats(self) -> Dict[str, Any]:
        return {"topics": list(self._subscribers.keys()),
                "total_messages": self._message_count,
                "subscriber_count": sum(len(s) for s in self._subscribers.values())}

class CommandBus(EventBus):
    """Bus for command-style messages (single handler per command)."""
    async def send(self, command: str, payload: Any) -> Any:
        handlers = self._subscribers.get(command, [])
        if not handlers:
            raise KeyError(f"No handler for command: {command}")
        handler = handlers[0]
        result = handler(BusMessage(topic=command, payload=payload))
        if asyncio.iscoroutine(result):
            result = await result
        return result

class ServiceBus(EventBus):
    """Service-to-service communication bus with request/reply."""
    def __init__(self) -> None:
        super().__init__()
        self._reply_queues: Dict[str, asyncio.Queue] = {}

    async def request(self, topic: str, payload: Any, timeout: float = 10.0) -> Any:
        reply_id = f"reply_{self._message_count}"
        self._reply_queues[reply_id] = asyncio.Queue()
        await self.publish(topic, {"payload": payload, "reply_to": reply_id})
        try:
            return await asyncio.wait_for(self._reply_queues[reply_id].get(), timeout=timeout)
        finally:
            self._reply_queues.pop(reply_id, None)

    async def reply(self, reply_id: str, response: Any) -> None:
        queue = self._reply_queues.get(reply_id)
        if queue:
            await queue.put(response)

UtilityBus = EventBus


