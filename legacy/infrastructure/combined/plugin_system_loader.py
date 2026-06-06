
from __future__ import annotations
"""
PluginSystemLoader — Combines plugin system + dynamic loader.
"""
import importlib, logging, os
from typing import Any, Dict



logger = logging.getLogger(__name__)

class PluginSystemLoader:
    """Load, manage, and hot-reload plugins."""

    def __init__(self, plugin_dir: str = "plugins") -> None:
        self._dir = plugin_dir
        self._plugins: Dict[str, Any] = {}
        self._hooks: Dict[str, list] = {}

    def scan(self) -> list:
        if not os.path.isdir(self._dir):
            return []
        return [f[:-3] for f in os.listdir(self._dir) if f.endswith('.py') and f != '__init__.py']

    def load(self, name: str) -> Any:
        try:
            mod = importlib.import_module(f"{self._dir}.{name}")
            self._plugins[name] = mod
            if hasattr(mod, 'register'):
                mod.register(self)
            logger.info("Plugin loaded: %s", name)
        except Exception as e:
            logger.error("Plugin load failed: %s: %s", name, e)

    def load_all(self) -> Any:
        for name in self.scan():
            self.load(name)

    def register_hook(self, event: str, fn: Any) -> None:
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(fn)

    async def trigger(self, event: str, data: dict=None) -> Any:
        for fn in self._hooks.get(event, []):
            try:
                data = await fn(data) if asyncio.iscoroutinefunction(fn) else fn(data)
            except Exception as e:
                logger.warning("Hook %s failed: %s", event, e)
        return data


