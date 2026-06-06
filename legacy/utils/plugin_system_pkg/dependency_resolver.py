
"""
plugin_system_pkg/dependency_resolver.py — DependencyResolver
Arki Engine v29.0.0
"""
from ._base import *  # noqa

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





