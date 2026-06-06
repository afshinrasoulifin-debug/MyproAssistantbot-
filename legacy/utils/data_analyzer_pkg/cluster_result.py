
"""
data_analyzer_pkg/cluster_result.py — ClusterResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class ClusterResult:
    """K-means clustering result."""
    k: int
    centroids: List[List[float]]
    labels: List[int]
    inertia: float
    iterations: int




