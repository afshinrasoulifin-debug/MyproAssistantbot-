
from __future__ import annotations
"""InfraPluginSystem — Plugin lifecycle management."""
import logging
from typing import Any, Dict



logger = logging.getLogger(__name__)

class InfraPluginSystem:
    """Register, load, enable/disable plugins."""

    def __init__(self) -> None:
        self._plugins: Dict[str, Any] = {}
        self._enabled: Dict[str, bool] = {}

    def register(self, name: str, plugin: Any) -> Any:
        self._plugins[name] = plugin
        self._enabled[name] = True

    def enable(self, name: str) -> Any:
        self._enabled[name] = True

    def disable(self, name: str) -> Any:
        self._enabled[name] = False

    def is_enabled(self, name: str) -> bool:
        return self._enabled.get(name, False)

    def get(self, name: str) -> Any:
        if self.is_enabled(name):
            return self._plugins.get(name)
        return None

    def list_plugins(self) -> Dict[str, bool]:
        return dict(self._enabled)


