
from __future__ import annotations
"""
tg_bot/utils/plugin_manager.py — Unified Plugin Manager v9.3
Consolidates: plugin_engine.py + plugin_system.py

Features:
  • Plugin lifecycle (load, enable, disable, unload)
  • Dependency resolution
  • Hook system for events
  • Plugin marketplace integration
  • Hot-reload support
"""
import importlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PluginState(Enum):
    UNLOADED = "unloaded"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class PluginMeta:
    name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)
    state: PluginState = PluginState.UNLOADED
    module: Any = None
    error: Optional[str] = None


class PluginManager:
    """
    Unified plugin management system.
    Handles plugin discovery, loading, lifecycle, and hooks.
    """

    def __init__(self, plugin_dir: str = "plugins") -> None:
        self._plugins: Dict[str, PluginMeta] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._plugin_dir = Path(plugin_dir)
        self._plugin_dir.mkdir(parents=True, exist_ok=True)
        self._stats = {"loaded": 0, "enabled": 0, "errors": 0}

    def discover(self) -> List[str]:
        """Discover available plugins in plugin directory."""
        found = []
        if self._plugin_dir.exists():
            for item in self._plugin_dir.iterdir():
                if item.is_dir() and (item / "__init__.py").exists():
                    found.append(item.name)
                elif item.suffix == ".py" and item.stem != "__init__":
                    found.append(item.stem)
        return found

    def load(self, name: str, module_path: str = None) -> bool:
        """Load a plugin by name."""
        try:
            if module_path:
                mod = importlib.import_module(module_path)
            else:
                mod = importlib.import_module(f"plugins.{name}")

            meta = PluginMeta(
                name=name,
                version=getattr(mod, "__version__", "1.0.0"),
                author=getattr(mod, "__author__", ""),
                description=getattr(mod, "__description__", ""),
                dependencies=getattr(mod, "__dependencies__", []),
                hooks=getattr(mod, "__hooks__", []),
                state=PluginState.LOADED,
                module=mod,
            )

            # Check dependencies
            for dep in meta.dependencies:
                if dep not in self._plugins or self._plugins[dep].state != PluginState.ENABLED:
                    meta.error = f"Missing dependency: {dep}"
                    meta.state = PluginState.ERROR
                    self._stats["errors"] += 1
                    break

            self._plugins[name] = meta
            self._stats["loaded"] += 1
            logger.info("Plugin loaded: %s v%s", name, meta.version)
            return True
        except Exception as e:
            self._plugins[name] = PluginMeta(
                name=name, state=PluginState.ERROR, error=str(e)
            )
            self._stats["errors"] += 1
            logger.error("Plugin load failed: %s — %s", name, e)
            return False

    def enable(self, name: str) -> bool:
        """Enable a loaded plugin."""
        plugin = self._plugins.get(name)
        if not plugin or plugin.state not in (PluginState.LOADED, PluginState.DISABLED):
            return False

        try:
            if hasattr(plugin.module, "on_enable"):
                plugin.module.on_enable()

            # Register hooks
            for hook_name in plugin.hooks:
                handler = getattr(plugin.module, f"hook_{hook_name}", None)
                if handler:
                    if hook_name not in self._hooks:
                        self._hooks[hook_name] = []
                    self._hooks[hook_name].append(handler)

            plugin.state = PluginState.ENABLED
            self._stats["enabled"] += 1
            return True
        except Exception as e:
            plugin.state = PluginState.ERROR
            plugin.error = str(e)
            return False

    def disable(self, name: str) -> bool:
        """Disable an enabled plugin."""
        plugin = self._plugins.get(name)
        if not plugin or plugin.state != PluginState.ENABLED:
            return False

        try:
            if hasattr(plugin.module, "on_disable"):
                plugin.module.on_disable()

            # Remove hooks
            for hook_name in plugin.hooks:
                if hook_name in self._hooks:
                    handler = getattr(plugin.module, f"hook_{hook_name}", None)
                    if handler and handler in self._hooks[hook_name]:
                        self._hooks[hook_name].remove(handler)

            plugin.state = PluginState.DISABLED
            self._stats["enabled"] -= 1
            return True
        except Exception as e:
            plugin.error = str(e)
            return False

    def unload(self, name: str) -> bool:
        """Unload a plugin completely."""
        if name in self._plugins:
            self.disable(name)
            del self._plugins[name]
            self._stats["loaded"] -= 1
            return True
        return False

    async def emit_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Emit a hook event to all registered handlers."""
        results = []
        for handler in self._hooks.get(hook_name, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(*args, **kwargs)
                else:
                    result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error("Hook %s handler error: %s", hook_name, e)
        return results

    def list_plugins(self) -> List[Dict]:
        """List all plugins with status."""
        return [
            {
                "name": p.name,
                "version": p.version,
                "state": p.state.value,
                "author": p.author,
                "description": p.description,
                "error": p.error,
            }
            for p in self._plugins.values()
        ]

    @property
    def stats(self) -> dict:
        return {**self._stats, "total": len(self._plugins)}


import asyncio

# ── TITANIUM v29.0 Integration ──


_manager: Optional[PluginManager] = None

def get_plugin_manager() -> PluginManager:
    global _manager
    if _manager is None:
        _manager = PluginManager()
    return _manager


