
"""
openrouter_client_pkg/cost_tracker.py — CostTracker
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class CostTracker:
    """Track API costs per user and model."""

    def __init__(self) -> None:
        self.requests: List[Dict[str, Any]] = []
        self.by_model: Dict[str, float] = defaultdict(float)
        self.by_user: Dict[str, float] = defaultdict(float)
        self.budgets: Dict[str, float] = {}
        self.total_cost: float = 0.0
        self.total_tokens: int = 0

    def record(self, model: str, cost: float,
               input_tokens: int, output_tokens: int,
               user_id: str = "default") -> None:
        """Record a request's cost."""
        self.requests.append({
            "model": model,
            "cost": cost,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "user_id": user_id,
            "timestamp": time.time(),
        })
        self.by_model[model] += cost
        self.by_user[user_id] += cost
        self.total_cost += cost
        self.total_tokens += input_tokens + output_tokens

    def set_budget(self, user_id: str, budget: float) -> None:
        """Set spending budget for a user."""
        self.budgets[user_id] = budget

    def check_budget(self, user_id: str) -> Tuple[bool, float]:
        """Check if user is within budget. Returns (within, remaining)."""
        if user_id not in self.budgets:
            return True, float("inf")
        spent = self.by_user.get(user_id, 0)
        remaining = self.budgets[user_id] - spent
        return remaining > 0, remaining

    def get_report(self, period_hours: float = 24) -> Dict[str, Any]:
        """Generate cost report."""
        cutoff = time.time() - period_hours * 3600
        recent = [r for r in self.requests if r["timestamp"] >= cutoff]

        return {
            "total_cost": round(self.total_cost, 4),
            "total_tokens": self.total_tokens,
            "total_requests": len(self.requests),
            "period_cost": round(sum(r["cost"] for r in recent), 4),
            "period_requests": len(recent),
            "by_model": {k: round(v, 4) for k, v in self.by_model.items()},
            "by_user": {k: round(v, 4) for k, v in self.by_user.items()},
        }


# ═══════════════════════════════════════════════════════════════════
# Circuit Breaker
# ═══════════════════════════════════════════════════════════════════



