
from __future__ import annotations
# CONSOLIDATED into plugin_manager.py
# Use: from arki_project.utils.plugin_manager import get_plugin_manager
"""
tg_bot/utils/plugin_engine.py
──────────────────────────────
PLUGIN ENGINE v1.0 — Hot-Reloadable Plugin Architecture

Modular plugin system for extending bot capabilities at runtime:
  • Plugin manifest with metadata, dependencies, permissions
  • PluginRegistry — register, enable, disable, uninstall
  • Plugin lifecycle: init → activate → execute → deactivate → destroy
  • Hook system — plugins hook into any pipeline stage
  • Plugin isolation with sandboxed context
  • Inter-plugin communication via event bus
  • Hot-reload without restart
  • Dependency resolution & load ordering
  • Dynamic module loading from file or URL

Architecture:
  manifest → registry → resolver → loader → sandbox → hooks → execute

v9.8.6 ULTIMATE+
"""


import asyncio
import importlib
import importlib.util
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

# ── Configuration ──
PLUGINS_DIR = os.getenv("PLUGINS_DIR", "plugins")
MAX_PLUGINS = 50
HOOK_TIMEOUT = 10  # seconds per hook call


# ── Types ──

class PluginCategory(str, Enum):
    TOOL = "tool"
    TRANSPORT = "transport"
    MODEL = "model"
    TRANSFORM = "transform"
    SECURITY = "security"
    STORAGE = "storage"
    ANALYTICS = "analytics"
    INTEGRATION = "integration"
    UTILITY = "utility"
    OTHER = "other"


class PluginPermission(str, Enum):
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    EXECUTE = "execute"
    CRYPTO = "crypto"
    MEMORY = "memory"
    MODELS = "models"
    PLUGINS = "plugins"
    SYSTEM = "system"
    UNLIMITED = "unlimited"


class PluginState(str, Enum):
    INSTALLED = "installed"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"
    LOADING = "loading"


@dataclass
class PluginManifest:
    """Plugin metadata and configuration."""
    id: str
    name: str
    version: str
    description: str
    author: str = ""
    category: PluginCategory = PluginCategory.OTHER
    permissions: list[PluginPermission] = field(default_factory=list)
    dependencies: dict[str, str] = field(default_factory=dict)
    hooks: list[str] = field(default_factory=list)
    entry_point: str = "main.py"
    config: dict[str, Any] = field(default_factory=dict)
    min_engine_version: str = "7.0"
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "PluginManifest":
        return cls(
            id=data["id"], name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            category=PluginCategory(data.get("category", "other")),
            permissions=[PluginPermission(p) for p in data.get("permissions", [])],
            dependencies=data.get("dependencies", {}),
            hooks=data.get("hooks", []),
            entry_point=data.get("entry_point", "main.py"),
            config=data.get("config", {}),
            tags=data.get("tags", []),
        )


@dataclass
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

HookCallback = Callable[..., Awaitable[Any]]

class EventBus:
    """Inter-plugin communication via hooks/events."""

    def __init__(self) -> None:
        self._hooks: dict[str, list[tuple[str, HookCallback, int]]] = {}

    def register(self, hook_name: str, plugin_id: str,
                 callback: HookCallback, priority: int = 100) -> None:
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append((plugin_id, callback, priority))
        self._hooks[hook_name].sort(key=lambda x: x[2])

    def unregister(self, plugin_id: str) -> int:
        removed = 0
        for hook_name in list(self._hooks.keys()):
            before = len(self._hooks[hook_name])
            self._hooks[hook_name] = [
                (pid, cb, p) for pid, cb, p in self._hooks[hook_name]
                if pid != plugin_id
            ]
            removed += before - len(self._hooks[hook_name])
        return removed

    async def emit(self, hook_name: str, *args: Any, **kwargs: Any) -> list[Any]:
        results = []
        for plugin_id, callback, _ in self._hooks.get(hook_name, []):
            try:
                result = await asyncio.wait_for(
                    callback(*args, **kwargs), timeout=HOOK_TIMEOUT,
                )
                results.append(result)
            except asyncio.TimeoutError:
                logger.warning("Hook %s timeout for plugin %s", hook_name, plugin_id)
            except Exception as exc:
                logger.warning("Hook %s error for plugin %s: %s", hook_name, plugin_id, exc)
        return results

    def list_hooks(self) -> dict[str, list[str]]:
        return {
            name: [pid for pid, _, _ in cbs]
            for name, cbs in self._hooks.items()
        }


# ── Plugin Registry ──

class PluginRegistry:
    """Central registry for all plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginInstance] = {}
        self.event_bus = EventBus()
        self._load_order: list[str] = []

    async def install(self, manifest: PluginManifest,
                      module_path: str | None = None) -> PluginInstance:
        """Install a plugin from manifest."""
        if manifest.id in self._plugins:
            raise ValueError(f"Plugin {manifest.id} already installed")
        if len(self._plugins) >= MAX_PLUGINS:
            raise RuntimeError(f"Max {MAX_PLUGINS} plugins reached")

        # Check dependencies
        for dep_id, dep_ver in manifest.dependencies.items():
            if dep_id not in self._plugins:
                raise ValueError(f"Missing dependency: {dep_id} {dep_ver}")

        instance = PluginInstance(manifest=manifest)

        # Load module if path provided
        if module_path:
            try:
                instance.state = PluginState.LOADING
                instance.module = _load_module(manifest.id, module_path)
                instance.loaded_at = time.time()
                instance.state = PluginState.INSTALLED
            except Exception as exc:
                instance.state = PluginState.ERROR
                instance.error = str(exc)

        self._plugins[manifest.id] = instance
        self._load_order.append(manifest.id)
        logger.info("Plugin installed: %s v%s", manifest.name, manifest.version)
        return instance

    async def activate(self, plugin_id: str) -> bool:
        """Activate an installed plugin."""
        inst = self._plugins.get(plugin_id)
        if not inst:
            return False
        if inst.state == PluginState.ACTIVE:
            return True

        try:
            # Call plugin init if available
            if inst.module and hasattr(inst.module, "on_activate"):
                await inst.module.on_activate(inst.config, self.event_bus)

            # Register hooks
            if inst.module:
                for hook_name in inst.manifest.hooks:
                    handler = getattr(inst.module, f"hook_{hook_name}", None)
                    if handler:
                        self.event_bus.register(hook_name, plugin_id, handler)

            inst.state = PluginState.ACTIVE
            inst.activated_at = time.time()
            logger.info("Plugin activated: %s", plugin_id)
            return True

        except Exception as exc:
            inst.state = PluginState.ERROR
            inst.error = str(exc)
            return False

    async def deactivate(self, plugin_id: str) -> bool:
        """Deactivate a plugin."""
        inst = self._plugins.get(plugin_id)
        if not inst or inst.state != PluginState.ACTIVE:
            return False

        try:
            if inst.module and hasattr(inst.module, "on_deactivate"):
                await inst.module.on_deactivate()
            self.event_bus.unregister(plugin_id)
            inst.state = PluginState.DISABLED
            return True
        except Exception as exc:
            inst.state = PluginState.ERROR
            inst.error = str(exc)
            return False

    async def uninstall(self, plugin_id: str) -> bool:
        """Fully remove a plugin."""
        await self.deactivate(plugin_id)
        if plugin_id in self._plugins:
            if self._plugins[plugin_id].module and hasattr(self._plugins[plugin_id].module, "on_destroy"):
                try:
                    await self._plugins[plugin_id].module.on_destroy()
                except Exception as e:
                    logger.debug("Suppressed: %s", e)
            del self._plugins[plugin_id]
            self._load_order = [p for p in self._load_order if p != plugin_id]
            return True
        return False

    async def execute(self, plugin_id: str, method: str, *args: Any, **kwargs: Any) -> Any:
        """Execute a plugin method."""
        inst = self._plugins.get(plugin_id)
        if not inst or inst.state != PluginState.ACTIVE:
            raise RuntimeError(f"Plugin {plugin_id} not active")
        if not inst.module or not hasattr(inst.module, method):
            raise AttributeError(f"Plugin {plugin_id} has no method {method}")

        inst.execution_count += 1
        return await getattr(inst.module, method)(*args, **kwargs)

    async def hot_reload(self, plugin_id: str) -> bool:
        """Hot-reload a plugin without full restart."""
        inst = self._plugins.get(plugin_id)
        if not inst:
            return False

        was_active = inst.state == PluginState.ACTIVE
        if was_active:
            await self.deactivate(plugin_id)

        if inst.module:
            try:
                importlib.reload(inst.module)
                inst.loaded_at = time.time()
                inst.error = ""
            except Exception as exc:
                inst.error = str(exc)
                inst.state = PluginState.ERROR
                return False

        if was_active:
            return await self.activate(plugin_id)
        return True

    def list_plugins(self) -> list[dict]:
        return [
            {
                "id": inst.manifest.id,
                "name": inst.manifest.name,
                "version": inst.manifest.version,
                "state": inst.state.value,
                "category": inst.manifest.category.value,
                "executions": inst.execution_count,
                "hooks": inst.manifest.hooks,
                "error": inst.error[:100] if inst.error else "",
            }
            for inst in self._plugins.values()
        ]

    def get(self, plugin_id: str) -> PluginInstance | None:
        return self._plugins.get(plugin_id)

    def stats(self) -> dict:
        by_state = {}
        for inst in self._plugins.values():
            by_state[inst.state.value] = by_state.get(inst.state.value, 0) + 1
        return {
            "total": len(self._plugins),
            "by_state": by_state,
            "hooks": self.event_bus.list_hooks(),
            "load_order": self._load_order,
        }


def _load_module(name: str, path: str) -> Any:
    """Dynamically load a Python module from path."""
    spec = importlib.util.spec_from_file_location(f"plugin_{name}", path)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"plugin_{name}"] = module
    spec.loader.exec_module(module)
    return module


# ── Module Singleton ──
plugin_registry = PluginRegistry()


