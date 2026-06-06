
"""
plugin_system_pkg/hook_registration.py — HookRegistration
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class HookRegistration:
    """Hook registration."""
    hook_name: str
    phase: HookPhase
    handler: Callable
    plugin_id: str
    priority: int = 0






