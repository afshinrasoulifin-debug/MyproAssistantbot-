
"""
plugin_system_pkg/plugin.py — Plugin
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class Plugin:
    """
    Base class for plugins.

    Override lifecycle methods to implement plugin behavior.
    """

    metadata: PluginMetadata

    def __init__(self, config: Dict[str, Any] = None) -> None:
        self.config = config or {}
        self.state = PluginState.UNLOADED
        self._storage: Dict[str, Any] = {}

    def on_init(self) -> None:
        """Called when plugin is initialized."""
        pass

    def on_start(self) -> None:
        """Called when plugin is started."""
        pass

    def on_stop(self) -> None:
        """Called when plugin is stopped."""
        pass

    def on_destroy(self) -> None:
        """Called when plugin is destroyed."""
        pass

    def on_config_change(self, old_config: Dict, new_config: Dict) -> None:
        """Called when configuration changes."""
        pass

    def health_check(self) -> Dict[str, Any]:
        """Return plugin health status."""
        return {"status": "ok", "state": self.state.value}


# ═══════════════════════════════════════════════════════════════════
# Event Bus
# ═══════════════════════════════════════════════════════════════════





