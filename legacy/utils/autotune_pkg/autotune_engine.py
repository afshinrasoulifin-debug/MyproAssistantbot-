
"""
autotune_pkg/autotune_engine.py — AutotuneEngine
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class AutotuneEngine:
    """
    Main autotuning engine.

    Combines Bayesian optimization, genetic algorithms,
    multi-armed bandits, and feedback for holistic tuning.
    """

    def __init__(self, space: ParameterSpace) -> None:
        self.space = space
        self.bayesian = BayesianOptimizer(space)
        self.genetic = GeneticOptimizer(space)
        self.feedback = FeedbackEngine()
        self.all_trials: List[Trial] = []

    def suggest(self, method: str = "bayesian") -> Dict[str, Any]:
        """Suggest parameters using specified method."""
        if method == "bayesian":
            return self.bayesian.suggest()
        elif method == "genetic":
            if not self.genetic.population:
                self.genetic.initialize()
            return random.choice(self.genetic.population)
        elif method == "random":
            return self.space.sample()
        return self.bayesian.suggest()

    def report(self, params: Dict[str, Any], score: float,
               metrics: Optional[Dict[str, float]] = None) -> Trial:
        """Report evaluation result."""
        trial = self.bayesian.report(params, score, metrics)
        self.all_trials.append(trial)
        return trial

    def best(self) -> Optional[Trial]:
        """Get best trial across all methods."""
        if not self.all_trials:
            return None
        return max(self.all_trials, key=lambda t: t.score)

    def leaderboard(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Get top N trials."""
        sorted_trials = sorted(
            self.all_trials, key=lambda t: t.score, reverse=True,
        )
        return [t.to_dict() for t in sorted_trials[:top_n]]

    def export_best_config(self) -> Dict[str, Any]:
        """Export best configuration."""
        best = self.best()
        if not best:
            return {}
        return {
            "params": best.params,
            "score": best.score,
            "metrics": best.metrics,
            "total_trials": len(self.all_trials),
        }



# ═══════════════════════════════════════════════════════════════════════
# APEX AUTOTUNE v2 — Context-Adaptive Parameter Engine (DEEP)
# ═══════════════════════════════════════════════════════════════════════
#
# Architecture:
#   ┌──────────────────────┐
#   │   User Message        │
#   │   + History (last 4)  │
#   └──────────┬───────────┘
#              ▼
#   ┌──────────────────────┐
#   │  CONTEXT DETECTION    │ ← 20 regex patterns, 5 context types
#   │  (code/creative/      │   Current msg: 3× weight
#   │   analytical/conv/    │   History: 1× weight
#   │   chaotic)            │   Persian keywords supported
#   └──────────┬───────────┘
#              ▼
#   ┌──────────────────────┐
#   │  CONFIDENCE BLENDING  │ ← <60%: blend with balanced profile
#   │                       │   ≥60%: pure context profile
#   └──────────┬───────────┘
#              ▼
#   ┌──────────────────────┐
#   │  CONVERSATION ADAPT   │ ← >10 msgs: boost repetition penalty
#   └──────────┬───────────┘
#              ▼
#   ┌──────────────────────┐
#   │  EMA FEEDBACK LOOP    │ ← α=0.3, min 3 samples, max 50% weight
#   │  (learned_profiles)   │   Push toward ↑positive, away from ↓negative
#   └──────────┬───────────┘
#              ▼
#   ┌──────────────────────┐
#   │  USER OVERRIDES       │ ← Absolute precedence
#   └──────────┬───────────┘
#              ▼
#   ┌──────────────────────┐
#   │  BOUNDS ENFORCEMENT   │ ← Clamp to API-valid ranges
#   └──────────────────────┘
#
# Ported from: APEX-main/src/lib/autotune.ts + autotune-feedback.ts
# Version: 4.0.0-DEEP (Phase 1-5 hardened)
# ═══════════════════════════════════════════════════════════════════════




