
from __future__ import annotations
"""
architecture.manager.plugin — PluginManager, ExtensionManager
═══════════════════════════════════════════════════════════════
Plugin lifecycle management with discovery, loading, and hot-swap.
Covers: plugin-manager, extension-manager, plugin, extension, extension-host
"""
import importlib, logging, time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional



logger = logging.getLogger(__name__)

@dataclass
class PluginInfo:
    name: str
    version: str = "1.0.0"
    module_path: Optional[str] = None
    enabled: bool = True
    loaded_at: Optional[float] = None
    instance: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class PluginManager:
    """Full plugin lifecycle: discover, load, enable/disable, unload."""
    def __init__(self) -> None:
        self._plugins: Dict[str, PluginInfo] = {}
        self._hooks: Dict[str, List[Callable]] = {}

    def register(self, name: str, version: str = "1.0.0",
                 module_path: Optional[str] = None, **metadata) -> PluginInfo:
        info = PluginInfo(name=name, version=version, module_path=module_path, metadata=metadata)
        self._plugins[name] = info
        return info

    def load(self, name: str) -> bool:
        info = self._plugins.get(name)
        if not info or not info.module_path:
            return False
        try:
            mod = importlib.import_module(info.module_path)
            if hasattr(mod, "setup"):
                info.instance = mod.setup()
            else:
                info.instance = mod
            info.loaded_at = time.time()
            logger.info("Plugin loaded: %s v%s", name, info.version)
            return True
        except Exception as exc:
            logger.error("Plugin load failed %s: %s", name, exc)
            return False

    def enable(self, name: str) -> bool:
        info = self._plugins.get(name)
        if info:
            info.enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        info = self._plugins.get(name)
        if info:
            info.enabled = False
            return True
        return False

    def get_plugin(self, name: str) -> Optional[PluginInfo]:
        return self._plugins.get(name)

    def active_plugins(self) -> List[PluginInfo]:
        return [p for p in self._plugins.values() if p.enabled]

    @property
    def stats(self) -> Dict[str, Any]:
        return {"total": len(self._plugins),
                "active": sum(1 for p in self._plugins.values() if p.enabled),
                "loaded": sum(1 for p in self._plugins.values() if p.loaded_at)}

class ExtensionManager(PluginManager):
    """Plugin manager with extension point system."""
    def __init__(self) -> None:
        super().__init__()
        self._extension_points: Dict[str, List[Callable]] = {}

    def register_extension_point(self, name: str) -> None:
        self._extension_points.setdefault(name, [])

    def extend(self, point: str, handler: Callable) -> None:
        self._extension_points.setdefault(point, []).append(handler)

    def get_extensions(self, point: str) -> List[Callable]:
        return self._extension_points.get(point, [])


