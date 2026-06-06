
"""
autotune_pkg/feedback_engine.py — FeedbackEngine
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class FeedbackEngine:
    """
    Collect and process user feedback for auto-tuning.

    Aggregates ratings, latency, quality scores, and
    custom metrics to guide optimization.
    """

    def __init__(self) -> None:
        self.ratings: List[Dict[str, Any]] = []
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.param_history: List[Dict[str, Any]] = []

    def record_feedback(
        self,
        params: Dict[str, Any],
        rating: float,
        latency_ms: float = 0,
        quality_score: float = 0,
        custom_metrics: Optional[Dict[str, float]] = None,
    ) -> None:
        """Record user feedback."""
        entry = {
            "params": params,
            "rating": rating,
            "latency_ms": latency_ms,
            "quality_score": quality_score,
            "timestamp": time.time(),
        }
        if custom_metrics:
            entry["custom"] = custom_metrics

        self.ratings.append(entry)
        self.metrics["rating"].append(rating)
        self.metrics["latency"].append(latency_ms)
        self.metrics["quality"].append(quality_score)

    def compute_composite_score(self, entry: Dict[str, Any],
                                weights: Optional[Dict[str, float]] = None) -> float:
        """Compute weighted composite score."""
        w = weights or {
            "rating": 0.4,
            "quality": 0.3,
            "latency": 0.3,
        }

        # Normalize latency (lower is better)
        max_lat = max(self.metrics["latency"]) if self.metrics["latency"] else 1
        norm_latency = 1 - (entry.get("latency_ms", 0) / max(max_lat, 1))

        score = (
            w.get("rating", 0) * entry.get("rating", 0)
            + w.get("quality", 0) * entry.get("quality_score", 0)
            + w.get("latency", 0) * norm_latency
        )
        return score

    def trend(self, metric: str = "rating",
              window: int = 10) -> Dict[str, float]:
        """Compute trend for a metric."""
        values = self.metrics.get(metric, [])
        if len(values) < window:
            return {"trend": 0, "current_mean": 0}

        recent = values[-window:]
        older = values[-2 * window:-window] if len(values) >= 2 * window else values[:window]

        recent_mean = sum(recent) / len(recent)
        older_mean = sum(older) / len(older) if older else recent_mean

        return {
            "trend": round(recent_mean - older_mean, 4),
            "current_mean": round(recent_mean, 4),
            "direction": "improving" if recent_mean > older_mean else "declining",
        }


# ═══════════════════════════════════════════════════════════════════
# Autotune Engine (Main Interface)
# ═══════════════════════════════════════════════════════════════════



