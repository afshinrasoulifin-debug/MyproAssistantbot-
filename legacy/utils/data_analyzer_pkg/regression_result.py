
"""
data_analyzer_pkg/regression_result.py — RegressionResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class RegressionResult:
    """Linear regression result."""
    slope: float
    intercept: float
    r_squared: float
    residuals: List[float]
    prediction_fn: Optional[Callable] = None

    def predict(self, x: float) -> float:
        return self.slope * x + self.intercept




