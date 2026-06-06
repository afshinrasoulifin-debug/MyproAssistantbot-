
"""Unified Plugin System — merged from plugin_system, plugin_engine, plugin_manager."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import importlib
import importlib.util
import json
import re
import time



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





class ConfigValidator:
    """Validate plugin configuration against a schema."""

    TYPES = {"string", "number", "boolean", "array", "object"}

    @classmethod
    def validate(cls, config: Dict[str, Any],
                 schema: Dict[str, Any]) -> List[str]:
        """
        Validate config against schema.

        Schema format:
        {
            "field_name": {
                "type": "string",
                "required": true,
                "default": "value",
                "min": 0,
                "max": 100,
                "pattern": "regex",
                "enum": ["a", "b"]
            }
        }
        """
        errors: List[str] = []

        for field_name, field_schema in schema.items():
            value = config.get(field_name)
            required = field_schema.get("required", False)

            # Required check
            if value is None:
                if required:
                    errors.append(f"Missing required field: {field_name}")
                continue

            # Type check
            expected_type = field_schema.get("type")
            if expected_type:
                if not cls._check_type(value, expected_type):
                    errors.append(
                        f"Field '{field_name}': expected {expected_type}, "
                        f"got {type(value).__name__}"
                    )
                    continue

            # Range check
            if isinstance(value, (int, float)):
                if "min" in field_schema and value < field_schema["min"]:
                    errors.append(
                        f"Field '{field_name}': value {value} below "
                        f"minimum {field_schema['min']}"
                    )
                if "max" in field_schema and value > field_schema["max"]:
                    errors.append(
                        f"Field '{field_name}': value {value} above "
                        f"maximum {field_schema['max']}"
                    )

            # Pattern check
            if isinstance(value, str) and "pattern" in field_schema:
                if not re.match(field_schema["pattern"], value):
                    errors.append(
                        f"Field '{field_name}': doesn't match pattern "
                        f"'{field_schema['pattern']}'"
                    )

            # Enum check
            if "enum" in field_schema and value not in field_schema["enum"]:
                errors.append(
                    f"Field '{field_name}': value '{value}' not in "
                    f"allowed values {field_schema['enum']}"
                )

        return errors

    @classmethod
    def apply_defaults(cls, config: Dict[str, Any],
                       schema: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values from schema."""
        result = dict(config)
        for field_name, field_schema in schema.items():
            if field_name not in result and "default" in field_schema:
                result[field_name] = field_schema["default"]
        return result

    @classmethod
    def _check_type(cls, value: Any, expected: str) -> bool:
        """Check if a value matches an expected type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected_type = type_map.get(expected)
        if expected_type is None:
            return True
        return isinstance(value, expected_type)


# ═══════════════════════════════════════════════════════════════════
# Plugin Manager (Main Interface)
# ═══════════════════════════════════════════════════════════════════



class DependencyResolver:
    """
    Topological dependency resolver with cycle detection.

    Uses Kahn's algorithm for topological sorting.
    """

    @classmethod
    def resolve(cls, plugins: Dict[str, PluginMetadata]) -> List[str]:
        """
        Resolve plugin load order.

        Returns topologically sorted list of plugin IDs.
        Raises ValueError on cyclic dependencies.
        """
        # Build adjacency list and in-degree count
        graph: Dict[str, Set[str]] = defaultdict(set)
        in_degree: Dict[str, int] = {pid: 0 for pid in plugins}

        for pid, meta in plugins.items():
            for dep in meta.dependencies:
                if dep.plugin_id in plugins:
                    graph[dep.plugin_id].add(pid)
                    in_degree[pid] = in_degree.get(pid, 0) + 1
                elif not dep.optional:
                    raise ValueError(
                        f"Plugin '{pid}' requires missing dependency "
                        f"'{dep.plugin_id}'"
                    )

        # Kahn's algorithm
        queue = [pid for pid, deg in in_degree.items() if deg == 0]
        order: List[str] = []

        while queue:
            node = queue.pop(0)
            order.append(node)

            for neighbor in graph.get(node, set()):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for cycles
        if len(order) != len(plugins):
            remaining = set(plugins.keys()) - set(order)
            cycle = cls._find_cycle(graph, remaining)
            raise ValueError(
                f"Cyclic dependency detected: {' → '.join(cycle)}"
            )

        return order

    @classmethod
    def _find_cycle(cls, graph: Dict[str, Set[str]],
                    nodes: Set[str]) -> List[str]:
        """Find a cycle in the dependency graph (for error reporting)."""
        visited: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> Optional[List[str]]:
            if node in visited:
                idx = path.index(node) if node in path else 0
                return path[idx:] + [node]
            visited.add(node)
            path.append(node)
            for neighbor in graph.get(node, set()):
                if neighbor in nodes:
                    result = dfs(neighbor)
                    if result:
                        return result
            path.pop()
            return None

        for node in nodes:
            visited.clear()
            path.clear()
            result = dfs(node)
            if result:
                return result

        return list(nodes)


# ═══════════════════════════════════════════════════════════════════
# Plugin Storage
# ═══════════════════════════════════════════════════════════════════



class EventBus:
    """
    Pub/sub event bus with wildcards and priority.

    Events: "plugin.*", "system.ready", "data.updated"
    Wildcards: "plugin.*" matches "plugin.loaded", "plugin.error"
    """

    def __init__(self) -> None:
        self.subscriptions: Dict[str, List[EventSubscription]] = defaultdict(list)
        self.history: List[Dict[str, Any]] = []
        self.max_history: int = 1000

    def subscribe(
        self,
        event: str,
        handler: Callable,
        plugin_id: str = "",
        priority: int = 0,
        once: bool = False,
        filter_fn: Optional[Callable] = None,
    ) -> str:
        """Subscribe to an event. Returns subscription ID."""
        sub = EventSubscription(
            event=event,
            handler=handler,
            plugin_id=plugin_id,
            priority=priority,
            once=once,
            filter_fn=filter_fn,
        )
        self.subscriptions[event].append(sub)
        # Sort by priority (higher first)
        self.subscriptions[event].sort(
            key=lambda s: s.priority, reverse=True,
        )
        return f"{plugin_id}:{event}"

    def unsubscribe(self, plugin_id: str, event: Optional[str] = None) -> int:
        """Unsubscribe a plugin from events."""
        count = 0
        events = [event] if event else list(self.subscriptions.keys())
        for ev in events:
            if ev in self.subscriptions:
                before = len(self.subscriptions[ev])
                self.subscriptions[ev] = [
                    s for s in self.subscriptions[ev]
                    if s.plugin_id != plugin_id
                ]
                count += before - len(self.subscriptions[ev])
        return count

    def publish(self, event: str, data: Any = None) -> List[Any]:
        """Publish an event. Returns handler results."""
        results = []
        to_remove: List[Tuple[str, EventSubscription]] = []

        # Find matching subscriptions (exact + wildcard)
        matching = self._find_matching(event)

        for sub in matching:
            # Apply filter
            if sub.filter_fn and not sub.filter_fn(data):
                continue

            try:
                result = sub.handler(event, data)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})

            if sub.once:
                to_remove.append((sub.event, sub))

        # Remove once-subscriptions
        for ev, sub in to_remove:
            if ev in self.subscriptions:
                self.subscriptions[ev] = [
                    s for s in self.subscriptions[ev] if s is not sub
                ]

        # Log
        self.history.append({
            "event": event,
            "data_type": type(data).__name__,
            "handlers": len(matching),
            "timestamp": time.time(),
        })
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        return results

    def _find_matching(self, event: str) -> List[EventSubscription]:
        """Find all subscriptions matching an event (including wildcards)."""
        matching = list(self.subscriptions.get(event, []))

        # Check wildcard patterns
        for pattern, subs in self.subscriptions.items():
            if "*" in pattern:
                regex = pattern.replace(".", "\\.").replace("*", ".*")
                if re.match(f"^{regex}$", event):
                    matching.extend(subs)

        # Sort by priority
        matching.sort(key=lambda s: s.priority, reverse=True)
        return matching


# ═══════════════════════════════════════════════════════════════════
# Hook System
# ═══════════════════════════════════════════════════════════════════



class EventSubscription:
    """Event subscription."""
    event: str
    handler: Callable
    plugin_id: str
    priority: int = 0
    once: bool = False
    filter_fn: Optional[Callable] = None




class HookPhase(Enum):
    """Hook execution phases."""
    BEFORE = "before"
    AFTER = "after"
    ERROR = "error"




class HookRegistration:
    """Hook registration."""
    hook_name: str
    phase: HookPhase
    handler: Callable
    plugin_id: str
    priority: int = 0




class HookSystem:
    """
    Hook system with before/after/error phases.

    Hooks allow plugins to intercept and modify behavior
    at defined extension points.
    """

    def __init__(self) -> None:
        self.hooks: Dict[str, List[HookRegistration]] = defaultdict(list)

    def register(
        self,
        hook_name: str,
        phase: HookPhase,
        handler: Callable,
        plugin_id: str,
        priority: int = 0,
    ) -> None:
        """Register a hook handler."""
        reg = HookRegistration(
            hook_name=hook_name,
            phase=phase,
            handler=handler,
            plugin_id=plugin_id,
            priority=priority,
        )
        self.hooks[hook_name].append(reg)
        self.hooks[hook_name].sort(
            key=lambda h: h.priority, reverse=True,
        )

    def unregister(self, plugin_id: str) -> None:
        """Unregister all hooks for a plugin."""
        for name in list(self.hooks.keys()):
            self.hooks[name] = [
                h for h in self.hooks[name]
                if h.plugin_id != plugin_id
            ]

    def execute(
        self,
        hook_name: str,
        phase: HookPhase,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute hook chain for a phase."""
        handlers = [
            h for h in self.hooks.get(hook_name, [])
            if h.phase == phase
        ]

        for handler_reg in handlers:
            try:
                result = handler_reg.handler(context)
                if isinstance(result, dict):
                    context.update(result)
            except Exception as e:
                context["_hook_error"] = str(e)
                if phase != HookPhase.ERROR:
                    self.execute(hook_name, HookPhase.ERROR, context)
                break

        return context


# ═══════════════════════════════════════════════════════════════════
# Dependency Resolver
# ═══════════════════════════════════════════════════════════════════



class Permission(Enum):
    """Plugin capabilities/permissions."""
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    DATABASE = "database"
    EXECUTE = "execute"
    ADMIN = "admin"
    EVENTS = "events"
    HOOKS = "hooks"
    STORAGE = "storage"


# ═══════════════════════════════════════════════════════════════════
# Semantic Versioning
# ═══════════════════════════════════════════════════════════════════



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




class PluginDependency:
    """Plugin dependency specification."""
    plugin_id: str
    version_constraint: str = ">=0.0.0"
    optional: bool = False

    def is_satisfied_by(self, version: SemVer) -> bool:
        return version.satisfies(self.version_constraint)




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



class PluginManager:
    """
    Main plugin management engine.

    Handles plugin lifecycle, dependency resolution,
    event routing, and health monitoring.
    """

    def __init__(self) -> None:
        self.plugins: Dict[str, Plugin] = {}
        self.metadata: Dict[str, PluginMetadata] = {}
        self.event_bus = EventBus()
        self.hook_system = HookSystem()
        self.storage = PluginStorage()
        self.resolver = DependencyResolver()
        self.validator = ConfigValidator()

    def register(self, plugin_cls: Type[Plugin],
                 config: Optional[Dict[str, Any]] = None) -> str:
        """Register and initialize a plugin."""
        plugin = plugin_cls(config or {})
        meta = plugin.metadata
        pid = meta.id

        # Validate config
        if meta.config_schema:
            config = self.validator.apply_defaults(
                plugin.config, meta.config_schema,
            )
            errors = self.validator.validate(config, meta.config_schema)
            if errors:
                raise ValueError(f"Config errors: {'; '.join(errors)}")
            plugin.config = config

        # Check version conflicts
        if pid in self.plugins:
            existing = self.metadata[pid].version
            if meta.version <= existing:
                raise ValueError(
                    f"Plugin '{pid}' v{meta.version} conflicts with "
                    f"existing v{existing}"
                )

        self.plugins[pid] = plugin
        self.metadata[pid] = meta
        plugin.state = PluginState.LOADED

        self.event_bus.publish("plugin.loaded", {
            "plugin_id": pid, "version": str(meta.version),
        })

        return pid

    def initialize_all(self) -> List[str]:
        """Initialize all plugins in dependency order."""
        order = self.resolver.resolve(self.metadata)
        initialized: List[str] = []

        for pid in order:
            try:
                self._verify_dependencies(pid)
                plugin = self.plugins[pid]
                plugin.on_init()
                plugin.state = PluginState.INITIALIZED
                initialized.append(pid)
                self.event_bus.publish("plugin.initialized", {"plugin_id": pid})
            except Exception as e:
                self.plugins[pid].state = PluginState.ERROR
                self.event_bus.publish("plugin.error", {
                    "plugin_id": pid, "error": str(e),
                })

        return initialized

    def start_all(self) -> List[str]:
        """Start all initialized plugins."""
        started = []
        for pid, plugin in self.plugins.items():
            if plugin.state == PluginState.INITIALIZED:
                try:
                    plugin.on_start()
                    plugin.state = PluginState.STARTED
                    started.append(pid)
                    self.event_bus.publish("plugin.started", {"plugin_id": pid})
                except Exception:
                    plugin.state = PluginState.ERROR

        return started

    def stop_plugin(self, plugin_id: str) -> bool:
        """Stop a plugin."""
        if plugin_id not in self.plugins:
            return False

        plugin = self.plugins[plugin_id]
        try:
            plugin.on_stop()
            plugin.state = PluginState.STOPPED
            self.event_bus.unsubscribe(plugin_id)
            self.hook_system.unregister(plugin_id)
            self.event_bus.publish("plugin.stopped", {"plugin_id": plugin_id})
            return True
        except Exception:
            plugin.state = PluginState.ERROR
            return False

    def unload_plugin(self, plugin_id: str) -> bool:
        """Completely unload a plugin."""
        if plugin_id not in self.plugins:
            return False

        self.stop_plugin(plugin_id)
        plugin = self.plugins[plugin_id]
        plugin.on_destroy()
        plugin.state = PluginState.UNLOADED

        del self.plugins[plugin_id]
        del self.metadata[plugin_id]

        self.event_bus.publish("plugin.unloaded", {"plugin_id": plugin_id})
        return True

    def reload_plugin(self, plugin_id: str,
                      plugin_cls: Type[Plugin],
                      config: Optional[Dict[str, Any]] = None) -> bool:
        """Hot-reload a plugin."""
        self.unload_plugin(plugin_id)
        self.register(plugin_cls, config)
        self.initialize_all()
        self.start_all()
        return True

    def _verify_dependencies(self, plugin_id: str) -> None:
        """Verify all dependencies are satisfied."""
        meta = self.metadata[plugin_id]
        for dep in meta.dependencies:
            if dep.plugin_id not in self.metadata:
                if dep.optional:
                    continue
                raise ValueError(
                    f"Missing dependency: {dep.plugin_id}"
                )
            dep_version = self.metadata[dep.plugin_id].version
            if not dep_version.satisfies(dep.version_constraint):
                raise ValueError(
                    f"Dependency version mismatch: {dep.plugin_id} "
                    f"{dep_version} doesn't satisfy {dep.version_constraint}"
                )

    # ─── Query & Discovery ────────────────────────────────────────

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all plugins with status."""
        return [
            {
                **meta.to_dict(),
                "state": self.plugins[pid].state.value,
            }
            for pid, meta in self.metadata.items()
        ]

    def search(self, query: str) -> List[PluginMetadata]:
        """Search plugins by name, description, or tags."""
        q = query.lower()
        return [
            meta for meta in self.metadata.values()
            if (q in meta.name.lower()
                or q in meta.description.lower()
                or any(q in tag.lower() for tag in meta.tags))

        ]

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        return self.plugins.get(plugin_id)

    def health_check(self) -> Dict[str, Dict[str, Any]]:
        """Run health check on all plugins."""
        results = {}
        for pid, plugin in self.plugins.items():
            try:
                results[pid] = plugin.health_check()
            except Exception as e:
                results[pid] = {"status": "error", "error": str(e)}
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get plugin system statistics."""
        states = defaultdict(int)
        for plugin in self.plugins.values():
            states[plugin.state.value] += 1

        return {
            "total_plugins": len(self.plugins),
            "states": dict(states),
            "events_published": len(self.event_bus.history),
            "storage_plugins": len(self.storage.stores),
        }


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




class PluginMetadata:
    """Plugin metadata."""
    id: str
    name: str
    version: SemVer
    description: str = ""
    author: str = ""
    license: str = "MIT"
    homepage: str = ""
    dependencies: List[PluginDependency] = field(default_factory=list)
    permissions: Set[Permission] = field(default_factory=set)
    tags: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": str(self.version),
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "dependencies": [
                {"plugin": d.plugin_id, "version": d.version_constraint}
                for d in self.dependencies
            ],
            "permissions": [p.value for p in self.permissions],
            "tags": self.tags,
        }


# ═══════════════════════════════════════════════════════════════════
# Plugin Base Class
# ═══════════════════════════════════════════════════════════════════



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






class PluginStorage:
    """Isolated key-value storage for plugins."""

    def __init__(self) -> None:
        self.stores: Dict[str, Dict[str, Any]] = defaultdict(dict)

    def get(self, plugin_id: str, key: str,
            default: Any = None) -> Any:
        """Get a value from plugin storage."""
        return self.stores.get(plugin_id, {}).get(key, default)

    def set(self, plugin_id: str, key: str, value: Any) -> None:
        """Set a value in plugin storage."""
        self.stores[plugin_id][key] = value

    def delete(self, plugin_id: str, key: str) -> bool:
        """Delete a key from plugin storage."""
        if plugin_id in self.stores and key in self.stores[plugin_id]:
            del self.stores[plugin_id][key]
            return True
        return False

    def list_keys(self, plugin_id: str) -> List[str]:
        """List all keys for a plugin."""
        return list(self.stores.get(plugin_id, {}).keys())

    def clear(self, plugin_id: str) -> None:
        """Clear all storage for a plugin."""
        self.stores.pop(plugin_id, None)

    def size(self, plugin_id: str) -> int:
        """Get storage size in bytes."""
        data = self.stores.get(plugin_id, {})
        return len(json.dumps(data))

    def export_all(self) -> Dict[str, Dict[str, Any]]:
        """Export all storage."""
        return dict(self.stores)

    def import_all(self, data: Dict[str, Dict[str, Any]]) -> None:
        """Import storage data."""
        for plugin_id, store in data.items():
            self.stores[plugin_id] = store


# ═══════════════════════════════════════════════════════════════════
# Config Validator
# ═══════════════════════════════════════════════════════════════════



class SemVer:
    """Semantic version (major.minor.patch)."""
    major: int
    minor: int
    patch: int
    prerelease: str = ""

    @classmethod
    def parse(cls, version: str) -> "SemVer":
        """Parse version string."""
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$", version.strip())
        if not m:
            raise ValueError(f"Invalid version: {version}")
        return cls(
            major=int(m.group(1)),
            minor=int(m.group(2)),
            patch=int(m.group(3)),
            prerelease=m.group(4) or "",
        )

    def __str__(self) -> str:
        v = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            v += f"-{self.prerelease}"
        return v

    def __lt__(self, other: "SemVer") -> bool:
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        return self.patch < other.patch

    def __le__(self, other: "SemVer") -> bool:
        return self == other or self < other

    def __gt__(self, other: "SemVer") -> bool:
        return not self <= other

    def __ge__(self, other: "SemVer") -> bool:
        return not self < other

    def satisfies(self, constraint: str) -> bool:
        """
        Check if version satisfies a constraint.

        Supports: ^1.2.3 (compatible), ~1.2.3 (approximate),
                  >=1.2.3, <=1.2.3, =1.2.3, >1.2.3, <1.2.3
        """
        constraint = constraint.strip()

        if constraint.startswith("^"):
            # Compatible: same major, >= minor.patch
            target = SemVer.parse(constraint[1:])
            return self.major == target.major and self >= target

        elif constraint.startswith("~"):
            # Approximate: same major.minor, >= patch
            target = SemVer.parse(constraint[1:])
            return (
                self.major == target.major
                and self.minor == target.minor
                and self.patch >= target.patch
            )

        elif constraint.startswith(">="):
            return self >= SemVer.parse(constraint[2:])
        elif constraint.startswith("<="):
            return self <= SemVer.parse(constraint[2:])
        elif constraint.startswith(">"):
            return self > SemVer.parse(constraint[1:])
        elif constraint.startswith("<"):
            return self < SemVer.parse(constraint[1:])
        elif constraint.startswith("="):
            return self == SemVer.parse(constraint[1:])
        else:
            return self == SemVer.parse(constraint)


# ═══════════════════════════════════════════════════════════════════
# Plugin Metadata
# ═══════════════════════════════════════════════════════════════════



# ══════════════════════════════════════════════════════════════
# v10.4 Advanced Plugin System
# ══════════════════════════════════════════════════════════════

class PluginDependencyResolver:
    """Resolve plugin load order based on dependencies."""

    def __init__(self) -> None:
        self._plugins: dict[str, dict] = {}  # name -> {deps: [...], loaded: bool}

    def register(self, name: str, depends_on: list[str] | None = None) -> Any:
        self._plugins[name] = {"deps": depends_on or [], "loaded": False}

    def resolve_order(self) -> list[str]:
        """Topological sort for load order."""
        resolved: list[str] = []
        visited: set[str] = set()
        temp: set[str] = set()

        def visit(name: str) -> Any:
            if name in temp:
                return  # Cycle — skip
            if name in visited:
                return
            temp.add(name)
            for dep in self._plugins.get(name, {}).get("deps", []):
                if dep in self._plugins:
                    visit(dep)
            temp.discard(name)
            visited.add(name)
            resolved.append(name)

        for name in self._plugins:
            visit(name)
        return resolved

    def check_missing(self) -> list[str]:
        """Find plugins with unresolvable dependencies."""
        all_names = set(self._plugins.keys())
        missing = []
        for name, info in self._plugins.items():
            for dep in info["deps"]:
                if dep not in all_names:
                    missing.append(f"{name} requires {dep}")
        return missing


class HotReloader:
    """Watch plugin files and reload on change."""

    def __init__(self) -> None:
        self._watched: dict[str, float] = {}  # path -> last_mtime

    def watch(self, path: str) -> Any:
        import os
        try:
            self._watched[path] = os.path.getmtime(path)
        except OSError:
            self._watched[path] = 0

    def check_changes(self) -> list[str]:
        """Return paths that have changed since last check."""
        import os
        changed = []
        for path, mtime in self._watched.items():
            try:
                current = os.path.getmtime(path)
                if current > mtime:
                    changed.append(path)
                    self._watched[path] = current
            except OSError:
                pass
        return changed

    def reload_module(self, module_name: str) -> bool:
        """Reload a Python module by name."""
        import importlib, sys
        try:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
                return True
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)
        return False


