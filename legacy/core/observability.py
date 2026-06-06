
from __future__ import annotations
"""
core/observability.py — Unified Observability Layer v10.4.1
════════════════════════════════════════════════════════════
Single source of truth for metrics, tracing, and alerts across
all infrastructure components.

Features:
  - Distributed request tracing with span trees
  - Counter/gauge/histogram metrics
  - Alert rules with severity and cooldown
  - Correlation IDs across handler → pipeline → AI → DB
  - Performance percentile tracking (p50, p95, p99)
  - Export-ready (Prometheus/JSON format)
"""

import logging
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DISTRIBUTED TRACING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class Span:
    """A single tracing span."""
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    operation: str
    service: str
    start_time: float
    end_time: float = 0.0
    status: str = "ok"
    tags: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        if self.end_time <= 0:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    def add_event(self, name: str, **kwargs) -> None:
        self.events.append({"name": name, "ts": time.time(), **kwargs})

    def finish(self, status: str = "ok") -> Any:
        self.end_time = time.time()
        self.status = status

    def to_dict(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "operation": self.operation,
            "service": self.service,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status,
            "tags": self.tags,
            "events": self.events,
        }


class Tracer:
    """Distributed tracing with correlation IDs."""

    def __init__(self, max_traces: int = 1000) -> None:
        self._traces: Dict[str, List[Span]] = {}
        self._max = max_traces
        self._active_spans: Dict[str, Span] = {}  # span_id → Span

    def start_trace(self, operation: str, service: str = "arki", **tags) -> Span:
        """Start a new root trace."""
        trace_id = uuid.uuid4().hex[:16]
        span = self._create_span(trace_id, None, operation, service, tags)
        return span

    def start_span(self, parent: Span, operation: str, service: str = "", **tags) -> Span:
        """Start a child span."""
        return self._create_span(
            parent.trace_id, parent.span_id, operation,
            service or parent.service, tags,
        )

    def _create_span(self, trace_id: str, parent_id: Optional[str],
                     operation: str, service: str, tags: Dict) -> Span:
        span_id = uuid.uuid4().hex[:8]
        span = Span(
            trace_id=trace_id, span_id=span_id,
            parent_id=parent_id, operation=operation,
            service=service, start_time=time.time(), tags=tags,
        )
        self._active_spans[span_id] = span
        self._traces.setdefault(trace_id, []).append(span)
        # Evict old traces
        if len(self._traces) > self._max:
            oldest = next(iter(self._traces))
            del self._traces[oldest]
        return span

    def finish_span(self, span: Span, status: str = "ok") -> Any:
        span.finish(status)
        self._active_spans.pop(span.span_id, None)

    @asynccontextmanager
    async def trace(self, operation: str, service: str = "arki",
                    parent: Optional[Span] = None, **tags) -> Any:
        """Context manager for tracing."""
        if parent:
            span = self.start_span(parent, operation, service, **tags)
        else:
            span = self.start_trace(operation, service, **tags)
        try:
            yield span
        except Exception as e:
            span.add_event("error", error=str(e)[:200])
            span.finish("error")
            raise
        else:
            span.finish("ok")

    @contextmanager
    def trace_sync(self, operation: str, service: str = "arki",
                   parent: Optional[Span] = None, **tags) -> Any:
        """Synchronous context manager for tracing."""
        if parent:
            span = self.start_span(parent, operation, service, **tags)
        else:
            span = self.start_trace(operation, service, **tags)
        try:
            yield span
        except Exception as e:
            span.add_event("error", error=str(e)[:200])
            span.finish("error")
            raise
        else:
            span.finish("ok")

    def get_trace(self, trace_id: str) -> List[Dict]:
        spans = self._traces.get(trace_id, [])
        return [s.to_dict() for s in spans]

    def get_slow_traces(self, min_duration_ms: float = 1000, limit: int = 20) -> List[Dict]:
        """Find traces slower than threshold."""
        slow = []
        for trace_id, spans in self._traces.items():
            root = spans[0] if spans else None
            if root and root.duration_ms >= min_duration_ms:
                slow.append({
                    "trace_id": trace_id,
                    "operation": root.operation,
                    "duration_ms": round(root.duration_ms, 2),
                    "span_count": len(spans),
                    "status": root.status,
                })
        slow.sort(key=lambda x: -x["duration_ms"])
        return slow[:limit]

    @property
    def stats(self) -> Dict:
        return {
            "total_traces": len(self._traces),
            "active_spans": len(self._active_spans),
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# METRICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class Histogram:
    """Streaming histogram with percentile support."""
    values: Deque[float] = field(default_factory=lambda: deque(maxlen=10000))
    _sum: float = 0.0
    _count: int = 0

    def observe(self, value: float) -> Any:
        self.values.append(value)
        self._sum += value
        self._count += 1

    def percentile(self, p: float) -> float:
        if not self.values:
            return 0.0
        sorted_vals = sorted(self.values)
        idx = int(len(sorted_vals) * p / 100.0)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    @property
    def p50(self) -> float:
        return self.percentile(50)

    @property
    def p95(self) -> float:
        return self.percentile(95)

    @property
    def p99(self) -> float:
        return self.percentile(99)

    @property
    def avg(self) -> float:
        return self._sum / max(1, self._count)

    def summary(self) -> Dict:
        return {
            "count": self._count,
            "avg": round(self.avg, 2),
            "p50": round(self.p50, 2),
            "p95": round(self.p95, 2),
            "p99": round(self.p99, 2),
            "min": round(min(self.values), 2) if self.values else 0,
            "max": round(max(self.values), 2) if self.values else 0,
        }


class MetricsRegistry:
    """Central metrics registry with counter, gauge, histogram support."""

    def __init__(self) -> None:
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, Histogram] = {}
        self._labels: Dict[str, Dict[str, str]] = {}

    # Counters
    def inc(self, name: str, value: float = 1.0, **labels) -> Any:
        key = self._label_key(name, labels)
        self._counters[key] += value
        if labels:
            self._labels[key] = labels

    def counter(self, name: str, **labels) -> float:
        return self._counters.get(self._label_key(name, labels), 0.0)

    # Gauges
    def set_gauge(self, name: str, value: float, **labels) -> None:
        key = self._label_key(name, labels)
        self._gauges[key] = value
        if labels:
            self._labels[key] = labels

    def gauge(self, name: str, **labels) -> float:
        return self._gauges.get(self._label_key(name, labels), 0.0)

    # Histograms
    def observe(self, name: str, value: float, **labels) -> Any:
        key = self._label_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = Histogram()
        self._histograms[key].observe(value)
        if labels:
            self._labels[key] = labels

    def histogram(self, name: str, **labels) -> Optional[Dict]:
        key = self._label_key(name, labels)
        h = self._histograms.get(key)
        return h.summary() if h else None

    def _label_key(self, name: str, labels: Dict) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    # Export
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        for key, val in sorted(self._counters.items()):
            lines.append(f"arki_{key.replace('.', '_')} {val}")
        for key, val in sorted(self._gauges.items()):
            lines.append(f"arki_{key.replace('.', '_')} {val}")
        for key, h in sorted(self._histograms.items()):
            base = f"arki_{key.replace('.', '_')}"
            lines.append(f"{base}_count {h._count}")
            lines.append(f"{base}_avg {h.avg:.2f}")
            lines.append(f"{base}_p95 {h.p95:.2f}")
        return "\n".join(lines)

    def export_json(self) -> Dict:
        """Export all metrics as JSON."""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                k: v.summary() for k, v in self._histograms.items()
            },
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ALERT SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    """A single alert rule."""
    name: str
    condition: Callable[[], bool]
    severity: AlertSeverity = AlertSeverity.WARNING
    message: str = ""
    cooldown_seconds: float = 300.0
    last_fired: float = 0.0
    fire_count: int = 0


@dataclass
class AlertEvent:
    ts: float
    rule_name: str
    severity: str
    message: str


class AlertManager:
    """Manages alert rules and firing."""

    def __init__(self, max_history: int = 500) -> None:
        self._rules: Dict[str, AlertRule] = {}
        self._history: Deque[AlertEvent] = deque(maxlen=max_history)
        self._handlers: List[Callable] = []

    def add_rule(self, rule: AlertRule) -> None:
        self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> None:
        self._rules.pop(name, None)

    def on_alert(self, handler: Callable) -> None:
        """Register alert handler: fn(AlertEvent)."""
        self._handlers.append(handler)

    def check_all(self) -> List[AlertEvent]:
        """Evaluate all rules and fire alerts."""
        fired = []
        now = time.time()
        for rule in self._rules.values():
            if now - rule.last_fired < rule.cooldown_seconds:
                continue
            try:
                if rule.condition():
                    event = AlertEvent(
                        ts=now, rule_name=rule.name,
                        severity=rule.severity.value,
                        message=rule.message,
                    )
                    rule.last_fired = now
                    rule.fire_count += 1
                    self._history.append(event)
                    fired.append(event)
                    for h in self._handlers:
                        try:
                            h(event)
                        except Exception as _err:
                            logger.warning("Suppressed error: %s", _err)
            except Exception as e:
                logger.error("Alert rule '%s' evaluation error: %s", rule.name, e)
        return fired

    def get_history(self, last_n: int = 50) -> List[Dict]:
        return [
            {"ts": e.ts, "rule": e.rule_name, "severity": e.severity, "message": e.message}
            for e in list(self._history)[-last_n:]
        ]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GLOBAL OBSERVABILITY INSTANCE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class Observability:
    """Unified observability — single access point for tracing, metrics, alerts."""

    _instance: Optional["Observability"] = None

    def __new__(cls) -> Any:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self) -> Any:
        self.tracer = Tracer()
        self.metrics = MetricsRegistry()
        self.alerts = AlertManager()

    def reset(self) -> Any:
        """Reset for testing."""
        self._init()

    def full_dashboard(self) -> Dict:
        """Complete observability dashboard."""
        return {
            "tracing": self.tracer.stats,
            "slow_traces": self.tracer.get_slow_traces(limit=10),
            "metrics": self.metrics.export_json(),
            "recent_alerts": self.alerts.get_history(20),
        }


# Convenience access
def get_observability() -> Observability:
    return Observability()


