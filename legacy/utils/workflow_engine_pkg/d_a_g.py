
"""
workflow_engine_pkg/d_a_g.py — DAG
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class DAG:
    """
    Directed Acyclic Graph implementation.

    Supports cycle detection, topological sorting,
    and dependency resolution.
    """

    def __init__(self) -> None:
        self.adjacency: Dict[str, List[str]] = defaultdict(list)
        self.in_degree: Dict[str, int] = defaultdict(int)
        self.nodes: Set[str] = set()

    def add_node(self, node_id: str) -> None:
        """Add a node to the graph."""
        self.nodes.add(node_id)
        if node_id not in self.in_degree:
            self.in_degree[node_id] = 0

    def add_edge(self, source: str, target: str) -> None:
        """Add a directed edge from source to target."""
        self.adjacency[source].append(target)
        self.in_degree[target] = self.in_degree.get(target, 0) + 1
        self.nodes.add(source)
        self.nodes.add(target)

    def has_cycle(self) -> bool:
        """
        Detect cycles using Kahn's algorithm.

        Returns True if a cycle is found.
        """
        in_degree = dict(self.in_degree)
        for node in self.nodes:
            if node not in in_degree:
                in_degree[node] = 0

        queue = deque([n for n in self.nodes if in_degree.get(n, 0) == 0])
        visited = 0

        while queue:
            node = queue.popleft()
            visited += 1
            for neighbor in self.adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return visited != len(self.nodes)

    def topological_sort(self) -> List[str]:
        """
        Topological sort using Kahn's algorithm.

        Returns nodes in execution order.
        Raises ValueError if graph has cycles.
        """
        if self.has_cycle():
            raise ValueError("Workflow contains a cycle — cannot sort")

        in_degree = dict(self.in_degree)
        for node in self.nodes:
            if node not in in_degree:
                in_degree[node] = 0

        queue = deque(
            sorted([n for n in self.nodes if in_degree.get(n, 0) == 0])
        )
        result: List[str] = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in sorted(self.adjacency.get(node, [])):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def get_dependencies(self, node_id: str) -> Set[str]:
        """Get all nodes that must complete before this node."""
        deps: Set[str] = set()
        for source, targets in self.adjacency.items():
            if node_id in targets:
                deps.add(source)
        return deps

    def get_dependents(self, node_id: str) -> Set[str]:
        """Get all nodes that depend on this node."""
        return set(self.adjacency.get(node_id, []))

    def get_independent_groups(self) -> List[List[str]]:
        """
        Get groups of nodes that can execute in parallel.

        Returns list of levels, where each level contains
        nodes with no dependencies on the same level.
        """
        order = self.topological_sort()
        levels: Dict[str, int] = {}

        for node in order:
            deps = self.get_dependencies(node)
            if not deps:
                levels[node] = 0
            else:
                levels[node] = max(levels.get(d, 0) for d in deps) + 1

        groups: Dict[int, List[str]] = defaultdict(list)
        for node, level in levels.items():
            groups[level].append(node)

        return [groups[i] for i in sorted(groups.keys())]


# ═══════════════════════════════════════════════════════════════════
# Workflow Builder
# ═══════════════════════════════════════════════════════════════════



