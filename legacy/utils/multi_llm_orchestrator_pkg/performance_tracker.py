
"""
multi_llm_orchestrator_pkg/performance_tracker.py — PerformanceTracker
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class PerformanceTracker:
    """Track model performance over time for quality regression detection."""

    def __init__(self, window_size: int = 100):
        self._history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._window = window_size

    def record(self, model_id: str, response: ModelResponse) -> None:
        entry = {
            "timestamp": time.time(),
            "confidence": response.confidence,
            "latency_ms": response.latency_ms,
            "cost": response.cost,
            "refusal": response.refusal,
            "error": bool(response.error),
            "tokens": response.total_tokens,
        }
        self._history[model_id].append(entry)
        if len(self._history[model_id]) > self._window:
            self._history[model_id] = self._history[model_id][-self._window:]

    def get_model_stats(self, model_id: str) -> dict:
        entries = self._history.get(model_id, [])
        if not entries:
            return {}

        return {
            "calls": len(entries),
            "avg_confidence": sum(e["confidence"] for e in entries) / len(entries),
            "avg_latency_ms": sum(e["latency_ms"] for e in entries) / len(entries),
            "total_cost": sum(e["cost"] for e in entries),
            "refusal_rate": sum(1 for e in entries if e["refusal"]) / len(entries),
            "error_rate": sum(1 for e in entries if e["error"]) / len(entries),
        }

    def get_all_stats(self) -> Dict[str, dict]:
        return {mid: self.get_model_stats(mid) for mid in self._history}




