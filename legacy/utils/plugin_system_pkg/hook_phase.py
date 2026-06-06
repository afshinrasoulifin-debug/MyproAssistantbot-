
"""
plugin_system_pkg/hook_phase.py — HookPhase
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class HookPhase(Enum):
    """Hook execution phases."""
    BEFORE = "before"
    AFTER = "after"
    ERROR = "error"






