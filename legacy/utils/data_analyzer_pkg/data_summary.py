
"""
data_analyzer_pkg/data_summary.py — DataSummary
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class DataSummary:
    """Summary of an entire dataset."""
    rows: int
    columns: int
    column_stats: List[ColumnStats]
    correlations: Dict[str, Dict[str, float]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)




