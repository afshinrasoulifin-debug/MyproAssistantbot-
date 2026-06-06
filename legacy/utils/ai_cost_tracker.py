
from __future__ import annotations
"""
tg_bot/utils/ai_cost_tracker.py — AI Cost Tracking v9.3
Tracks token usage and estimated costs per user/handler/model.
"""
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

# Approximate costs per 1M tokens (USD)
MODEL_COSTS = {
    "gemini-2.5-pro": {"input": 0.15, "output": 0.60},
    "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
    "llama-3.3-70b": {"input": 0.59, "output": 0.79},
    "qwen-qwq-32b": {"input": 0.20, "output": 0.20},
    "default": {"input": 0.50, "output": 1.00},
}


@dataclass
class UsageRecord:
    """Single usage record."""
    timestamp: float
    user_id: int
    model: str
    handler: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class AICostTracker:
    """Tracks AI token usage and costs."""

    def __init__(self) -> None:
        self._records: List[UsageRecord] = []
        self._by_user: Dict[int, float] = defaultdict(float)
        self._by_model: Dict[str, float] = defaultdict(float)
        self._by_handler: Dict[str, float] = defaultdict(float)
        self._total_tokens = 0
        self._total_cost = 0.0

    def record(self, user_id: int, model: str, handler: str,
               input_tokens: int, output_tokens: int) -> Any:
        """Record a usage event."""
        costs = MODEL_COSTS.get(model, MODEL_COSTS["default"])
        cost = (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1_000_000

        record = UsageRecord(
            timestamp=time.time(),
            user_id=user_id,
            model=model,
            handler=handler,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )
        self._records.append(record)
        self._by_user[user_id] += cost
        self._by_model[model] += cost
        self._by_handler[handler] += cost
        self._total_tokens += input_tokens + output_tokens
        self._total_cost += cost

    def get_user_cost(self, user_id: int) -> float:
        return self._by_user.get(user_id, 0.0)

    def get_daily_cost(self) -> float:
        cutoff = time.time() - 86400
        return sum(r.cost_usd for r in self._records if r.timestamp > cutoff)

    def get_top_users(self, n: int = 10) -> List[Dict]:
        sorted_users = sorted(self._by_user.items(), key=lambda x: x[1], reverse=True)
        return [{"user_id": uid, "cost_usd": round(cost, 4)} for uid, cost in sorted_users[:n]]

    def get_model_breakdown(self) -> Dict[str, float]:
        return {k: round(v, 4) for k, v in self._by_model.items()}

    @property
    def stats(self) -> dict:
        return {
            "total_tokens": self._total_tokens,
            "total_cost_usd": round(self._total_cost, 4),
            "daily_cost_usd": round(self.get_daily_cost(), 4),
            "records": len(self._records),
            "unique_users": len(self._by_user),
            "models_used": len(self._by_model),
        }


_tracker: Optional[AICostTracker] = None

def get_cost_tracker() -> AICostTracker:
    global _tracker
    if _tracker is None:
        _tracker = AICostTracker()
    return _tracker


def detect_anomalies(self, threshold_multiplier: float = 3.0) -> list:
    """Detect users with anomalous token usage."""
    if not self._by_user:
        return []
    avg_cost = sum(self._by_user.values()) / len(self._by_user)
    threshold = avg_cost * threshold_multiplier
    anomalies = []
    for user_id, cost in self._by_user.items():
        if cost > threshold:
            anomalies.append({
                "user_id": user_id,
                "cost_usd": round(cost, 4),
                "ratio": round(cost / max(0.0001, avg_cost), 1),
            })
    return sorted(anomalies, key=lambda x: x["cost_usd"], reverse=True)

def get_budget_alert(self, daily_budget: float = 10.0) -> dict:
    """Check if daily budget is exceeded."""
    daily = self.get_daily_cost()
    return {
        "daily_cost": round(daily, 4),
        "budget": daily_budget,
        "exceeded": daily > daily_budget,
        "utilization_pct": round(daily / max(0.01, daily_budget) * 100, 1),
    }


# v9.6: Prometheus metrics with prometheus_client
try:
    from prometheus_client import Counter, Gauge, Histogram
    AI_REQUEST_TOTAL = Counter('ai_request_total', 'Total AI requests', ['model', 'provider'])
    AI_COST_USD = Counter('ai_cost_usd_total', 'Total AI cost in USD', ['model'])
    AI_LATENCY = Histogram('ai_latency_seconds', 'AI response latency', ['model'])
    AI_TOKEN_INPUT = Counter('ai_input_tokens_total', 'Total input tokens', ['model'])
    AI_TOKEN_OUTPUT = Counter('ai_output_tokens_total', 'Total output tokens', ['model'])
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False

def push_prometheus_metrics(model: str, provider: str = '', input_tokens: int = 0, output_tokens: int = 0, cost: float = 0.0, latency: float = 0.0) -> Any:
    """Push metrics to Prometheus collectors."""
    if not _HAS_PROMETHEUS:
        return
    AI_REQUEST_TOTAL.labels(model=model, provider=provider).inc()
    AI_COST_USD.labels(model=model).inc(cost)
    AI_TOKEN_INPUT.labels(model=model).inc(input_tokens)
    AI_TOKEN_OUTPUT.labels(model=model).inc(output_tokens)
    if latency > 0:
        AI_LATENCY.labels(model=model).observe(latency)


def export_cost_metrics() -> dict:
    """Export cost metrics in Prometheus-compatible format."""
    tracker = get_cost_tracker()
    return {
        "ai_total_cost_usd": getattr(tracker, '_total_cost', 0.0),
        "ai_total_requests": getattr(tracker, '_total_requests', 0),
        "ai_cost_per_model": getattr(tracker, '_cost_per_model', {}),
    }


