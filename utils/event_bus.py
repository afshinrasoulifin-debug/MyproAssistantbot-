
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/event_bus.py — Internal Event Bus v3.3
═══════════════════════════════════════════════════════════════
Pub/sub event bus connecting all system components.
Enables real automation: handlers → events → automation rules → actions.
"""
import asyncio, logging, time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class Event:
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    event_id: str = ""

@dataclass
class Subscription:
    event_type: str
    handler: Callable
    name: str = ""
    filter_fn: Optional[Callable[[Event], bool]] = None
    priority: int = 0
    call_count: int = 0
    last_called: float = 0.0

class EventBus:
    """Async pub/sub event bus with filtering, prioritization, and history."""

    # Standard event types
    USER_MESSAGE = "user.message"
    USER_COMMAND = "user.command"
    AI_REQUEST = "ai.request"
    AI_RESPONSE = "ai.response"
    AI_ERROR = "ai.error"
    MODEL_SWITCH = "model.switch"
    PAYMENT_RECEIVED = "payment.received"
    SUBSCRIPTION_CHANGE = "subscription.change"
    QUOTA_WARNING = "quota.warning"
    QUOTA_EXCEEDED = "quota.exceeded"
    SEARCH_PERFORMED = "search.performed"
    CONTENT_GENERATED = "content.generated"
    REMINDER_TRIGGERED = "reminder.triggered"
    MONITOR_ALERT = "monitor.alert"
    AUTOMATION_FIRED = "automation.fired"
    HEALTH_ALERT = "health.alert"
    CAMPAIGN_EVENT = "campaign.event"

    def __init__(self, max_history: int = 1000) -> None:
        self._subs: Dict[str, List[Subscription]] = defaultdict(list)
        self._wildcard_subs: List[Subscription] = []
        self._history: List[Event] = []
        self._max_history = max_history
        self._event_counter = 0
        self._processing = False
        self._pending: asyncio.Queue = asyncio.Queue()
        self._stats = {"published": 0, "delivered": 0, "errors": 0}

    def subscribe(self, event_type: str, handler: Callable,
                 name: str = "", filter_fn: Optional[Callable] = None,
                 priority: int = 0) -> Subscription:
        sub = Subscription(
            event_type=event_type, handler=handler, name=name or handler.__name__,
            filter_fn=filter_fn, priority=priority,
        )
        if event_type == "*":
            self._wildcard_subs.append(sub)
        else:
            self._subs[event_type].append(sub)
            self._subs[event_type].sort(key=lambda s: s.priority, reverse=True)
        logger.debug("Subscribed %s to %s", sub.name, event_type)
        return sub

    def unsubscribe(self, event_type: str, name: str) -> bool:
        subs = self._wildcard_subs if event_type == "*" else self._subs.get(event_type, [])
        for i, sub in enumerate(subs):
            if sub.name == name:
                subs.pop(i)
                return True
        return False

    async def publish(self, event_type: str, data: Dict[str, Any] = None,
                     source: str = "") -> int:
        """Publish event, returns number of handlers invoked."""
        self._event_counter += 1
        event = Event(
            type=event_type, data=data or {}, source=source,
            event_id=f"evt_{self._event_counter}",
        )
        self._stats["published"] += 1

        # Store history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Dispatch to subscribers
        handlers = list(self._subs.get(event_type, []))
        handlers.extend(self._wildcard_subs)
        delivered = 0

        for sub in handlers:
            if sub.filter_fn:
                try:
                    if not sub.filter_fn(event):
                        continue
                except ArkiBaseError:
                    continue
            try:
                result = sub.handler(event)
                if asyncio.iscoroutine(result):
                    await result
                sub.call_count += 1
                sub.last_called = time.time()
                delivered += 1
                self._stats["delivered"] += 1
            except ArkiBaseError as e:
                self._stats["errors"] += 1
                logger.error("Event handler %s error: %s", sub.name, e)

        return delivered

    def get_history(self, event_type: str = "", limit: int = 50) -> List[Dict]:
        events = self._history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return [
            {"type": e.type, "data": e.data, "source": e.source,
             "time": e.timestamp, "id": e.event_id}
            for e in events[-limit:]
        ]

    def list_subscriptions(self) -> Dict[str, List[str]]:
        result = {}
        for event_type, subs in self._subs.items():
            result[event_type] = [s.name for s in subs]
        if self._wildcard_subs:
            result["*"] = [s.name for s in self._wildcard_subs]
        return result

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "subscriptions": sum(len(s) for s in self._subs.values()) + len(self._wildcard_subs),
            "event_types": list(self._subs.keys()),
            "history_size": len(self._history),
        }


# Singleton
_bus: Optional[EventBus] = None
def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


