
"""
plugin_system_pkg/plugin_instance.py — PluginInstance
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class PluginInstance:
    """A loaded plugin instance."""
    manifest: PluginManifest
    state: PluginState = PluginState.INSTALLED
    config: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    loaded_at: float = 0
    activated_at: float = 0
    execution_count: int = 0
    module: Any = None
    _context: dict[str, Any] = field(default_factory=dict)


# ── Hook System ──





