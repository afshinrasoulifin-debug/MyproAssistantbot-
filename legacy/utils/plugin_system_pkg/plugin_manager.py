
"""
plugin_system_pkg/plugin_manager.py — PluginManager
Arki Engine v29.0.0
"""
from ._base import *  # noqa

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




