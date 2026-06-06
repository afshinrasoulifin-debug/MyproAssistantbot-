
"""
plugin_system_pkg/event_subscription.py — EventSubscription
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class EventSubscription:
    """Event subscription."""
    event: str
    handler: Callable
    plugin_id: str
    priority: int = 0
    once: bool = False
    filter_fn: Optional[Callable] = None






