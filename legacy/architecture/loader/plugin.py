
from __future__ import annotations
"""
architecture.loader.plugin — PluginLoader, ExtensionLoader
═══════════════════════════════════════════════════════════
Dynamic plugin and extension discovery and loading.
Covers: plugin-loader, extension-loader
"""
import importlib, logging, os
from typing import Any, Dict, List, Optional



logger = logging.getLogger(__name__)

class PluginLoader:
    """Discover and load plugins from directory."""
    def __init__(self, plugin_dir: str = "plugins") -> None:
        self.plugin_dir = plugin_dir
        self._plugins: Dict[str, Any] = {}

    def discover(self) -> List[str]:
        found = []
        if os.path.isdir(self.plugin_dir):
            for entry in os.listdir(self.plugin_dir):
                path = os.path.join(self.plugin_dir, entry)
                if os.path.isdir(path) and os.path.exists(os.path.join(path, "__init__.py")):
                    found.append(entry)
                elif entry.endswith(".py") and entry != "__init__.py":
                    found.append(entry[:-3])
        return found

    def load(self, name: str) -> Optional[Any]:
        try:
            mod = importlib.import_module(f"{self.plugin_dir}.{name}")
            self._plugins[name] = mod
            if hasattr(mod, "setup"):
                mod.setup()
            logger.info("Plugin loaded: %s", name)
            return mod
        except Exception as exc:
            logger.error("Plugin load error %s: %s", name, exc)
            return None

    def load_all(self) -> Dict[str, bool]:
        results = {}
        for name in self.discover():
            results[name] = self.load(name) is not None
        return results

    @property
    def loaded(self) -> List[str]:
        return list(self._plugins.keys())

class ExtensionLoader(PluginLoader):
    """Plugin loader with extension point registration."""
    def __init__(self, ext_dir: str = "extensions") -> None:
        super().__init__(ext_dir)
        self._extension_points: Dict[str, list] = {}

    def register_point(self, name: str) -> None:
        self._extension_points.setdefault(name, [])

    def extend(self, point: str, handler) -> None:
        self._extension_points.setdefault(point, []).append(handler)


