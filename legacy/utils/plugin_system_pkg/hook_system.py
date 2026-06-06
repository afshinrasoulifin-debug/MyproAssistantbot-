
"""
plugin_system_pkg/hook_system.py — HookSystem
Arki Engine v29.0.0
"""
from ._base import *  # noqa

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





