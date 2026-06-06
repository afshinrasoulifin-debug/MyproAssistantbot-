
"""
plugin_system_pkg/plugin_state.py — PluginState
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class PluginState(Enum):
    """Plugin lifecycle states."""
    UNLOADED = "unloaded"
    INSTALLED = "installed"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"
    DISABLED = "disabled"







