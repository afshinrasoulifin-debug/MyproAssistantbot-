
from __future__ import annotations
"""
tg_bot/orchestration/observatory.py — Observability Layer
═════════════════════════════════════════════════════════
Unified metrics, monitoring, and structured logging:
  • Request/response metrics (latency, errors, throughput)
  • Provider health dashboard
  • Cost tracking
  • Structured event logging
  • Health check endpoint data

Patterns covered:
  - runtime-hooks + middleware-chain + observability
  - orchestration-engine + provider-federation + observability-layer
  - distributed-ai-runtime + orchestration-layer + metrics-pipeline
  - ai-service + distributed-observability
"""

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List



# ProviderName import removed — not used in this module

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class RequestMetric:
    """Metrics for a single AI request."""
    request_id: str
    provider: str
    model_id: str
    latency_ms: float
    success: bool
    tokens_in: int = 0
    tokens_out: int = 0
    cached: bool = False
    timestamp: float = field(default_factory=time.time)
    error_type: str = ""


class Observatory:
    """Centralized observability for the orchestration layer.

    Collects metrics from all components and provides:
      - Real-time dashboards
      - Cost tracking
      - Anomaly detection
      - Health check data
    """

    def __init__(self, window_size: int = 1000) -> None:
        self._window_size = window_size
        self._requests: deque[RequestMetric] = deque(maxlen=window_size)

        # Counters
        self._total_requests = 0
        self._total_errors = 0
        self._total_cached = 0
        self._total_tokens_in = 0
        self._total_tokens_out = 0

        # Per-provider stats
        self._provider_requests: Dict[str, int] = defaultdict(int)
        self._provider_errors: Dict[str, int] = defaultdict(int)
        self._provider_latencies: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=200)
        )

        # Per-model stats
        self._model_requests: Dict[str, int] = defaultdict(int)
        self._model_latencies: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=200)
        )

        # Cost tracking
        self._cost_tracker: Dict[str, float] = defaultdict(float)

        # Events log
        self._events: deque[Dict[str, Any]] = deque(maxlen=500)

        # Boot time
        self._boot_time = time.time()

    # ── Record ─────────────────────────────────────────────

    def record_request(self, metric: RequestMetric) -> None:
        """Record a completed AI request."""
        self._requests.append(metric)
        self._total_requests += 1
        self._provider_requests[metric.provider] += 1
        self._model_requests[metric.model_id] += 1
        self._provider_latencies[metric.provider].append(metric.latency_ms)
        self._model_latencies[metric.model_id].append(metric.latency_ms)

        if not metric.success:
            self._total_errors += 1
            self._provider_errors[metric.provider] += 1

        if metric.cached:
            self._total_cached += 1

        self._total_tokens_in += metric.tokens_in
        self._total_tokens_out += metric.tokens_out

    def record_event(
        self,
        event_type: str,
        message: str,
        **data: Any,
    ) -> None:
        """Record a structured event (circuit breaker trip, failover, etc.)."""
        self._events.append({
            "type": event_type,
            "message": message,
            "timestamp": time.time(),
            **data,
        })
        logger.info("[Observatory] %s: %s", event_type, message)

    def record_cost(self, provider: str, model_id: str, cost: float) -> None:
        """Track cost for a request."""
        self._cost_tracker[provider] += cost
        self._cost_tracker[f"{provider}:{model_id}"] += cost
        self._cost_tracker["total"] += cost

    # ── Queries ────────────────────────────────────────────

    def get_dashboard(self) -> Dict[str, Any]:
        """Get full dashboard data."""
        uptime = time.time() - self._boot_time
        rps = self._total_requests / max(uptime, 1)

        return {
            "uptime_seconds": round(uptime),
            "total_requests": self._total_requests,
            "total_errors": self._total_errors,
            "total_cached": self._total_cached,
            "error_rate": round(
                self._total_errors / max(self._total_requests, 1), 3
            ),
            "cache_hit_rate": round(
                self._total_cached / max(self._total_requests, 1), 3
            ),
            "requests_per_second": round(rps, 2),
            "tokens": {
                "total_in": self._total_tokens_in,
                "total_out": self._total_tokens_out,
            },
            "providers": self._get_provider_summary(),
            "models": self._get_model_summary(),
            "costs": dict(self._cost_tracker),
            "recent_events": list(self._events)[-10:],
        }

    def get_health_check(self) -> Dict[str, Any]:
        """Data for /health endpoint."""
        return {
            "status": "healthy" if self._is_healthy() else "degraded",
            "uptime": round(time.time() - self._boot_time),
            "total_requests": self._total_requests,
            "error_rate": round(
                self._total_errors / max(self._total_requests, 1), 4
            ),
            "providers": {
                name: {
                    "requests": count,
                    "errors": self._provider_errors.get(name, 0),
                    "avg_latency_ms": self._avg_latency(name),
                }
                for name, count in self._provider_requests.items()
            },
        }

    def get_provider_stats(self, provider: str) -> Dict[str, Any]:
        """Detailed stats for a single provider."""
        latencies = list(self._provider_latencies.get(provider, []))
        return {
            "requests": self._provider_requests.get(provider, 0),
            "errors": self._provider_errors.get(provider, 0),
            "avg_latency_ms": self._avg_from_list(latencies),
            "p50_latency_ms": self._percentile(latencies, 0.5),
            "p95_latency_ms": self._percentile(latencies, 0.95),
            "p99_latency_ms": self._percentile(latencies, 0.99),
            "error_rate": round(
                self._provider_errors.get(provider, 0)
                / max(self._provider_requests.get(provider, 0), 1),
                3,
            ),
        }

    # ── Helpers ────────────────────────────────────────────

    def _get_provider_summary(self) -> Dict[str, Dict]:
        return {
            name: {
                "requests": count,
                "errors": self._provider_errors.get(name, 0),
                "avg_latency_ms": self._avg_latency(name),
            }
            for name, count in self._provider_requests.items()
        }

    def _get_model_summary(self) -> Dict[str, Dict]:
        return {
            model: {
                "requests": count,
                "avg_latency_ms": self._avg_from_list(
                    list(self._model_latencies.get(model, []))
                ),
            }
            for model, count in self._model_requests.items()
        }

    def _avg_latency(self, provider: str) -> float:
        latencies = self._provider_latencies.get(provider, deque())
        return self._avg_from_list(list(latencies))

    @staticmethod
    def _avg_from_list(values: List[float]) -> float:
        if not values:
            return 0.0
        return round(sum(values) / len(values), 1)

    @staticmethod
    def _percentile(values: List[float], pct: float) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        idx = min(int(len(sorted_vals) * pct), len(sorted_vals) - 1)
        return round(sorted_vals[idx], 1)

    def _is_healthy(self) -> bool:
        """Simple health heuristic."""
        if self._total_requests < 10:
            return True
        error_rate = self._total_errors / self._total_requests
        return error_rate < 0.5

    def reset(self) -> None:
        """Reset all metrics."""
        self._requests.clear()
        self._total_requests = 0
        self._total_errors = 0
        self._total_cached = 0
        self._total_tokens_in = 0
        self._total_tokens_out = 0
        self._provider_requests.clear()
        self._provider_errors.clear()
        self._provider_latencies.clear()
        self._model_requests.clear()
        self._model_latencies.clear()
        self._cost_tracker.clear()
        self._events.clear()
        self._boot_time = time.time()


