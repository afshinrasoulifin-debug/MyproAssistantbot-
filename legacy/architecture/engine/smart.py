
from __future__ import annotations
"""
architecture.engine.smart — SmartEngine, AdaptiveEngine, PerformanceEngine, ActionEngine
════════════════════════════════════════════════════════════════════════════════════════
AI-aware engines that adapt behavior based on context, performance, and user patterns.
Covers: smart-engine, adaptive-engine, performance-engine, action-engine
"""
import logging, time, statistics
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class SmartEngine:
    """Context-aware decision engine for AI operations."""
    def __init__(self) -> None:
        self._strategies: Dict[str, Callable] = {}
        self._user_profiles: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
            "request_count": 0, "avg_complexity": 0.5,
            "preferred_style": "detailed", "last_active": 0,
        })

    def register_strategy(self, name: str, fn: Callable) -> None:
        self._strategies[name] = fn

    def analyze_user(self, user_id: int) -> Dict[str, Any]:
        return dict(self._user_profiles[user_id])

    def update_user(self, user_id: int, **kwargs) -> None:
        profile = self._user_profiles[user_id]
        profile.update(kwargs)
        profile["request_count"] += 1
        profile["last_active"] = time.time()

    def select_strategy(self, user_id: int, context: Dict[str, Any]) -> str:
        profile = self._user_profiles[user_id]
        complexity = context.get("complexity", profile["avg_complexity"])
        if complexity > 0.8:
            return "deep_analysis"
        elif complexity > 0.5:
            return "balanced"
        return "quick_response"

    def execute_smart(self, user_id: int, context: Dict[str, Any]) -> Any:
        strategy = self.select_strategy(user_id, context)
        fn = self._strategies.get(strategy)
        if fn:
            return fn(context)
        return None

class AdaptiveEngine:
    """Adapts AI parameters based on feedback and success rates."""
    def __init__(self) -> None:
        self._params: Dict[str, float] = {
            "temperature": 0.7, "max_tokens": 32768,
            "top_p": 0.9, "presence_penalty": 0.1,
        }
        self._feedback: List[Tuple[Dict[str, float], float]] = []

    def get_params(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        ctx = context or {}
        params = dict(self._params)
        # Adapt based on task type
        task = ctx.get("task_type", "general")
        if task == "creative":
            params["temperature"] = min(params["temperature"] + 0.15, 1.0)
        elif task == "analytical":
            params["temperature"] = max(params["temperature"] - 0.2, 0.1)
        elif task == "code":
            params["temperature"] = 0.2
            params["max_tokens"] = 8192
        return params

    def record_feedback(self, params: Dict[str, float], score: float) -> None:
        self._feedback.append((params, score))
        # Adjust base params towards better-scoring configs
        if len(self._feedback) >= 10:
            top = sorted(self._feedback, key=lambda x: x[1], reverse=True)[:5]
            for key in self._params:
                vals = [p[0].get(key, self._params[key]) for p in top]
                self._params[key] = statistics.mean(vals)

    @property
    def current_params(self) -> Dict[str, float]:
        return dict(self._params)

class PerformanceEngine:
    """Track and optimize performance metrics across all operations."""
    def __init__(self) -> None:
        self._metrics: Dict[str, List[float]] = defaultdict(list)
        self._thresholds: Dict[str, float] = {}
        self._alerts: List[Dict[str, Any]] = []

    def record(self, metric: str, value: float) -> None:
        self._metrics[metric].append(value)
        # Keep last 1000 samples
        if len(self._metrics[metric]) > 1000:
            self._metrics[metric] = self._metrics[metric][-500:]
        # Check threshold
        if metric in self._thresholds and value > self._thresholds[metric]:
            self._alerts.append({"metric": metric, "value": value,
                                 "threshold": self._thresholds[metric], "time": time.time()})

    def set_threshold(self, metric: str, max_value: float) -> None:
        self._thresholds[metric] = max_value

    def get_stats(self, metric: str) -> Dict[str, float]:
        vals = self._metrics.get(metric, [])
        if not vals:
            return {"count": 0}
        return {
            "count": len(vals), "mean": statistics.mean(vals),
            "median": statistics.median(vals),
            "min": min(vals), "max": max(vals),
            "p95": sorted(vals)[int(len(vals) * 0.95)] if len(vals) >= 20 else max(vals),
        }

    def all_stats(self) -> Dict[str, Dict[str, float]]:
        return {m: self.get_stats(m) for m in self._metrics}

class ActionEngine:
    """Maps intents to executable actions with validation."""
    def __init__(self) -> None:
        self._actions: Dict[str, Callable] = {}
        self._validators: Dict[str, Callable] = {}
        self._history: List[Dict[str, Any]] = []

    def register(self, name: str, action: Callable,
                 validator: Optional[Callable] = None) -> None:
        self._actions[name] = action
        if validator:
            self._validators[name] = validator

    async def execute(self, name: str, context: Dict[str, Any]) -> Any:
        if name not in self._actions:
            raise KeyError(f"Action '{name}' not registered")
        validator = self._validators.get(name)
        if validator and not validator(context):
            raise ValueError(f"Validation failed for action '{name}'")
        t0 = time.time()
        try:
            import asyncio
            result = self._actions[name](context)
            if asyncio.iscoroutine(result):
                result = await result
            self._history.append({"action": name, "time": time.time(),
                                  "duration_s": time.time()-t0, "success": True})
            return result
        except Exception as exc:
            self._history.append({"action": name, "time": time.time(),
                                  "duration_s": time.time()-t0, "success": False, "error": str(exc)})
            raise


