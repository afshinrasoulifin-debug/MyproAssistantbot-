
"""
plugin_system_pkg/plugin_registry.py — PluginRegistry
Arki Engine v29.0.0
"""
from ._base import *  # noqa

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








