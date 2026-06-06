
"""
data_analyzer_pkg/column_stats.py — ColumnStats
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class ColumnStats:
    """Statistics for a single column."""
    name: str
    dtype: str              # numeric | string | datetime | boolean
    count: int
    null_count: int
    unique_count: int
    # Numeric stats
    mean: Optional[float] = None
    median: Optional[float] = None
    mode: Optional[float] = None
    stddev: Optional[float] = None
    variance: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    q1: Optional[float] = None
    q3: Optional[float] = None
    iqr: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    cv: Optional[float] = None      # coefficient of variation
    # String stats
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    avg_length: Optional[float] = None
    # Top values
    top_values: List[Tuple[Any, int]] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {"name": self.name, "type": self.dtype, "count": self.count,
             "nulls": self.null_count, "unique": self.unique_count}
        if self.dtype == "numeric":
            d.update({
                "mean": round(self.mean, 4) if self.mean else None,
                "median": self.median,
                "stddev": round(self.stddev, 4) if self.stddev else None,
                "min": self.min_val, "max": self.max_val,
                "q1": self.q1, "q3": self.q3, "iqr": self.iqr,
                "skewness": round(self.skewness, 4) if self.skewness else None,
                "kurtosis": round(self.kurtosis, 4) if self.kurtosis else None,
            })
        return d




