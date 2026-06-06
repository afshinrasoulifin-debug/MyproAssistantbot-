
"""
autotune_pkg/trial.py — Trial
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class Trial:
    """Record of a single hyperparameter evaluation."""
    trial_id: int
    params: Dict[str, Any]
    score: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    status: str = "completed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "params": self.params,
            "score": round(self.score, 6),
            "metrics": {k: round(v, 6) for k, v in self.metrics.items()},
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status_code,
        }


# ═══════════════════════════════════════════════════════════════════
# Bayesian Optimization
# ═══════════════════════════════════════════════════════════════════



