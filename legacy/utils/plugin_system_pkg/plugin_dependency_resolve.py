
"""
plugin_system_pkg/plugin_dependency_resolve.py — PluginDependencyResolver
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class PluginDependencyResolver:
    """Resolve plugin load order based on dependencies."""

    def __init__(self):
        self._plugins: dict[str, dict] = {}  # name -> {deps: [...], loaded: bool}

    def register(self, name: str, depends_on: list[str] | None = None):
        self._plugins[name] = {"deps": depends_on or [], "loaded": False}

    def resolve_order(self) -> list[str]:
        """Topological sort for load order."""
        resolved: list[str] = []
        visited: set[str] = set()
        temp: set[str] = set()

        def visit(name: str):
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




