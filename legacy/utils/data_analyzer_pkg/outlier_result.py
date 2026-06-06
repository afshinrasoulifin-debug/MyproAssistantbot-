
"""
data_analyzer_pkg/outlier_result.py — OutlierResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class OutlierResult:
    """Outlier detection result."""
    method: str
    outlier_indices: List[int]
    outlier_values: List[float]
    threshold: float
    total: int
    outlier_count: int
    outlier_percent: float




