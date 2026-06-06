
"""
tg_bot/utils/telemetry_engine.py — REDIRECT to tracing.py v9.4
Consolidated into utils/tracing.py. This file is kept for backward compat.
"""
from arki_project.utils.tracing import setup_tracing, get_tracer, trace_span  # noqa: F401
from arki_project.utils.tracing import setup_tracing, get_tracer, trace_span
from typing import Any

__all__ = ['setup_tracing', 'get_tracer', 'trace_span']

import time
import logging

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

class TelemetryCollector:
    """Collect and report telemetry metrics."""

    def __init__(self) -> None:
        self._metrics: dict = {}
        self._start_time = time.time()

    def record(self, name: str, value: float) -> Any:
        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append({"value": value, "ts": time.time()})

    def get(self, name: str) -> list:
        return self._metrics.get(name, [])

    def summary(self) -> dict:
        return {
            "uptime": time.time() - self._start_time,
            "metric_count": len(self._metrics),
            "total_points": sum(len(v) for v in self._metrics.values()),
        }


# ══════════════════════════════════════════════════════════════
# v10.4 Advanced Telemetry & Observability
# ══════════════════════════════════════════════════════════════

import uuid as _uuid


class Span:
    """A single trace span."""

    def __init__(self, name: str, trace_id: str, parent_id: str | None = None) -> None:
        import time
        self.name = name
        self.trace_id = trace_id
        self.span_id = _uuid.uuid4().hex[:16]
        self.parent_id = parent_id
        self.start_time = time.time()
        self.end_time: float | None = None
        self.tags: dict[str, str] = {}
        self.status = "running"

    def finish(self, status: str = "ok") -> Any:
        import time
        self.end_time = time.time()
        self.status = status

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status,
            "tags": self.tags,
        }


class DistributedTracer:
    """Distributed tracing across modules."""

    def __init__(self) -> None:
        self._traces: dict[str, list[Span]] = {}

    def start_trace(self, name: str) -> Span:
        trace_id = _uuid.uuid4().hex[:16]
        span = Span(name, trace_id)
        self._traces[trace_id] = [span]
        return span

    def start_span(self, name: str, parent: Span) -> Span:
        span = Span(name, parent.trace_id, parent.span_id)
        if parent.trace_id not in self._traces:
            self._traces[parent.trace_id] = []
        self._traces[parent.trace_id].append(span)
        return span

    def finish_span(self, span: Span, status: str = "ok") -> Any:
        span.finish(status)

    def get_trace(self, trace_id: str) -> list[dict]:
        spans = self._traces.get(trace_id, [])
        return [s.to_dict() for s in spans]

    def summary(self) -> dict:
        total_traces = len(self._traces)
        total_spans = sum(len(s) for s in self._traces.values())
        errors = sum(
            1 for spans in self._traces.values()
            for s in spans if s.status == "error"
        )
        return {
            "total_traces": total_traces,
            "total_spans": total_spans,
            "error_spans": errors,
            "error_rate": errors / max(total_spans, 1),
        }


class MetricDashboard:
    """Aggregate metrics for dashboard display."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}

    def increment(self, name: str, value: int = 1) -> Any:
        self._counters[name] = self._counters.get(name, 0) + value

    def gauge(self, name: str, value: float) -> Any:
        self._gauges[name] = value

    def observe(self, name: str, value: float) -> Any:
        if name not in self._histograms:
            self._histograms[name] = []
        self._histograms[name].append(value)
        if len(self._histograms[name]) > 10000:
            self._histograms[name] = self._histograms[name][-5000:]

    def snapshot(self) -> dict:
        histo_summary = {}
        for name, values in self._histograms.items():
            s = sorted(values)
            histo_summary[name] = {
                "count": len(s),
                "avg": sum(s) / len(s),
                "p50": s[len(s) // 2],
                "p95": s[int(len(s) * 0.95)] if len(s) > 1 else s[0],
                "p99": s[int(len(s) * 0.99)] if len(s) > 1 else s[0],
            }
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": histo_summary,
        }


