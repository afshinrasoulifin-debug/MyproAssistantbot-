
"""
memory_store_pkg/memory_cluster.py — MemoryCluster
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class MemoryCluster:
    """Group related memories into clusters."""

    def __init__(self):
        self._clusters: dict[str, list[str]] = {}  # cluster_name -> memory_ids

    def add_to_cluster(self, cluster: str, memory_id: str):
        if cluster not in self._clusters:
            self._clusters[cluster] = []
        if memory_id not in self._clusters[cluster]:
            self._clusters[cluster].append(memory_id)

    def auto_cluster(self, memory_id: str, tags: list[str]):
        """Auto-assign to cluster based on tags."""
        for tag in tags:
            self.add_to_cluster(tag, memory_id)

    def get_cluster(self, cluster: str) -> list[str]:
        return self._clusters.get(cluster, [])

    def all_clusters(self) -> dict[str, int]:
        return {k: len(v) for k, v in self._clusters.items()}



