
from __future__ import annotations
"""
architecture.monitor.telemetry — TelemetryMonitor, DiagnosticsMonitor
════════════════════════════════════════════════════════════════════
Real-time telemetry and diagnostics collection.
Covers: telemetry, diagnostics, diagnostics-tools, monitor
"""
import logging, statistics, time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional



logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)

class TelemetryMonitor:
    """Collect, aggregate, and report telemetry metrics."""
    def __init__(self, max_history: int = 5000) -> None:
        self._metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._max_history = max_history

    def record(self, name: str, value: float, **tags) -> None:
        point = MetricPoint(name=name, value=value, tags=tags)
        self._metrics[name].append(point)
        if len(self._metrics[name]) > self._max_history:
            self._metrics[name] = self._metrics[name][-self._max_history//2:]

    def increment(self, name: str, amount: int = 1) -> int:
        self._counters[name] += amount
        return self._counters[name]

    def gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value

    def get_counter(self, name: str) -> int:
        return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> Optional[float]:
        return self._gauges.get(name)

    def aggregate(self, name: str, window_s: float = 300) -> Dict[str, float]:
        cutoff = time.time() - window_s
        points = [p for p in self._metrics.get(name, []) if p.timestamp >= cutoff]
        if not points:
            return {"count": 0}
        vals = [p.value for p in points]
        return {
            "count": len(vals),
            "mean": round(statistics.mean(vals), 4),
            "median": round(statistics.median(vals), 4),
            "min": round(min(vals), 4),
            "max": round(max(vals), 4),
            "sum": round(sum(vals), 4),
            "stddev": round(statistics.stdev(vals), 4) if len(vals) > 1 else 0,
        }

    def report(self) -> Dict[str, Any]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "metrics": {name: self.aggregate(name) for name in self._metrics},
        }

    def reset(self) -> None:
        self._metrics.clear()
        self._counters.clear()
        self._gauges.clear()

class DiagnosticsMonitor(TelemetryMonitor):
    """Extended telemetry with diagnostic capabilities."""
    def __init__(self) -> None:
        super().__init__()
        self._traces: List[Dict[str, Any]] = []
        self._alerts: List[Dict[str, Any]] = []
        self._thresholds: Dict[str, float] = {}

    def trace(self, operation: str, duration_s: float, success: bool = True, **details) -> None:
        self._traces.append({
            "operation": operation, "duration_s": round(duration_s, 4),
            "success": success, "time": time.time(), **details,
        })
        if len(self._traces) > 1000:
            self._traces = self._traces[-500:]
        self.record(f"trace.{operation}", duration_s)
        if not success:
            self.increment(f"error.{operation}")

    def set_alert_threshold(self, metric: str, threshold: float) -> None:
        self._thresholds[metric] = threshold

    def check_alerts(self) -> List[Dict[str, Any]]:
        new_alerts = []
        for metric, threshold in self._thresholds.items():
            agg = self.aggregate(metric, window_s=60)
            if agg.get("mean", 0) > threshold:
                alert = {"metric": metric, "threshold": threshold,
                         "current": agg["mean"], "time": time.time()}
                new_alerts.append(alert)
                self._alerts.append(alert)
        return new_alerts

    def recent_traces(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._traces[-limit:]

    def diagnostic_report(self) -> Dict[str, Any]:
        return {
            **self.report(),
            "traces": len(self._traces),
            "alerts": len(self._alerts),
            "recent_errors": [t for t in self._traces[-20:] if not t.get("success")],
        }


