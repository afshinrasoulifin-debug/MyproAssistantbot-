
from __future__ import annotations
"""AdaptiveEngine — Self-tuning engine that learns from feedback."""
import logging, time
from collections import defaultdict
from typing import Dict, Any



logger = logging.getLogger(__name__)

class AdaptiveEngine:
    """Engine that adapts parameters based on user feedback and performance."""

    def __init__(self) -> None:
        self._user_feedback: Dict[int, list] = defaultdict(list)
        self._parameter_overrides: Dict[int, Dict[str, Any]] = {}

    def record_feedback(self, user_id: int, rating: float, context: dict = None) -> Any:
        self._user_feedback[user_id].append({
            "rating": rating, "context": context or {}, "time": time.time()
        })
        self._adapt(user_id)

    def _adapt(self, user_id: int) -> Any:
        recent = self._user_feedback[user_id][-20:]
        avg_rating = sum(f["rating"] for f in recent) / len(recent)
        overrides = {}
        if avg_rating < 0.5:
            overrides["temperature"] = 0.5
            overrides["max_tokens"] = 65536
        elif avg_rating > 0.8:
            overrides["temperature"] = 0.7
        self._parameter_overrides[user_id] = overrides

    def get_params(self, user_id: int) -> Dict[str, Any]:
        return self._parameter_overrides.get(user_id, {})


