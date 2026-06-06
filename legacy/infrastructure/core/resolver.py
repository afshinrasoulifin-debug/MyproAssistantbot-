
from __future__ import annotations
"""Resolver — Resolve references, dependencies, and lookups."""
import logging
from typing import Any, Dict



logger = logging.getLogger(__name__)

class DependencyResolver:
    """Resolve component dependencies."""

    def __init__(self) -> None:
        self._registry: Dict[str, Any] = {}
        self._dependencies: Dict[str, list] = {}

    def register(self, name: str, component: Any, deps: list = None) -> Any:
        self._registry[name] = component
        self._dependencies[name] = deps or []

    def resolve(self, name: str) -> Any:
        return self._registry.get(name)

    def resolve_order(self) -> list:
        """Topological sort of dependencies."""
        visited = set()
        order = []
        def _visit(name: str) -> Any:
            if name in visited:
                return
            visited.add(name)
            for dep in self._dependencies.get(name, []):
                _visit(dep)
            order.append(name)
        for name in self._registry:
            _visit(name)
        return order


