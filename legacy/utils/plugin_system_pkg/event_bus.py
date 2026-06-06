
"""
plugin_system_pkg/event_bus.py — EventBus
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class EventBus:
    """
    Pub/sub event bus with wildcards and priority.

    Events: "plugin.*", "system.ready", "data.updated"
    Wildcards: "plugin.*" matches "plugin.loaded", "plugin.error"
    """

    def __init__(self) -> None:
        self.subscriptions: Dict[str, List[EventSubscription]] = defaultdict(list)
        self.history: List[Dict[str, Any]] = []
        self.max_history: int = 1000

    def subscribe(
        self,
        event: str,
        handler: Callable,
        plugin_id: str = "",
        priority: int = 0,
        once: bool = False,
        filter_fn: Optional[Callable] = None,
    ) -> str:
        """Subscribe to an event. Returns subscription ID."""
        sub = EventSubscription(
            event=event,
            handler=handler,
            plugin_id=plugin_id,
            priority=priority,
            once=once,
            filter_fn=filter_fn,
        )
        self.subscriptions[event].append(sub)
        # Sort by priority (higher first)
        self.subscriptions[event].sort(
            key=lambda s: s.priority, reverse=True,
        )
        return f"{plugin_id}:{event}"

    def unsubscribe(self, plugin_id: str, event: Optional[str] = None) -> int:
        """Unsubscribe a plugin from events."""
        count = 0
        events = [event] if event else list(self.subscriptions.keys())
        for ev in events:
            if ev in self.subscriptions:
                before = len(self.subscriptions[ev])
                self.subscriptions[ev] = [
                    s for s in self.subscriptions[ev]
                    if s.plugin_id != plugin_id
                ]
                count += before - len(self.subscriptions[ev])
        return count

    def publish(self, event: str, data: Any = None) -> List[Any]:
        """Publish an event. Returns handler results."""
        results = []
        to_remove: List[Tuple[str, EventSubscription]] = []

        # Find matching subscriptions (exact + wildcard)
        matching = self._find_matching(event)

        for sub in matching:
            # Apply filter
            if sub.filter_fn and not sub.filter_fn(data):
                continue

            try:
                result = sub.handler(event, data)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})

            if sub.once:
                to_remove.append((sub.event, sub))

        # Remove once-subscriptions
        for ev, sub in to_remove:
            if ev in self.subscriptions:
                self.subscriptions[ev] = [
                    s for s in self.subscriptions[ev] if s is not sub
                ]

        # Log
        self.history.append({
            "event": event,
            "data_type": type(data).__name__,
            "handlers": len(matching),
            "timestamp": time.time(),
        })
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        return results

    def _find_matching(self, event: str) -> List[EventSubscription]:
        """Find all subscriptions matching an event (including wildcards)."""
        matching = list(self.subscriptions.get(event, []))

        # Check wildcard patterns
        for pattern, subs in self.subscriptions.items():
            if "*" in pattern:
                regex = pattern.replace(".", "\\.").replace("*", ".*")
                if re.match(f"^{regex}$", event):
                    matching.extend(subs)

        # Sort by priority
        matching.sort(key=lambda s: s.priority, reverse=True)
        return matching


# ═══════════════════════════════════════════════════════════════════
# Hook System
# ═══════════════════════════════════════════════════════════════════





