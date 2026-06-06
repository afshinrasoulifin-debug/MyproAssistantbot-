
from __future__ import annotations
"""
utils/metrics_exporter.py — Prometheus Metrics Exporter v19.0
══════════════════════════════════════════════════════════════════
Real Prometheus-compatible /metrics endpoint.
Exports: request counts, latencies, circuit breaker states,
active users, model usage, error rates, system resources.

Works with or without prometheus_client library:
- With: native Counter/Histogram/Gauge objects
- Without: self-contained text format exporter
"""

import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Try native prometheus_client
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Info, CollectorRegistry,
        generate_latest, CONTENT_TYPE_LATEST,
    )
    _NATIVE = True
    _REGISTRY = CollectorRegistry()

    # ── Counters ──
    REQUEST_TOTAL = Counter(
        "arki_requests_total",
        "Total AI requests by provider and status",
        ["provider", "model", "status"],
        registry=_REGISTRY,
    )
    MESSAGES_TOTAL = Counter(
        "arki_messages_total",
        "Total messages processed by type",
        ["message_type"],
        registry=_REGISTRY,
    )
    ERRORS_TOTAL = Counter(
        "arki_errors_total",
        "Total errors by type",
        ["error_type", "provider"],
        registry=_REGISTRY,
    )

    # ── Histograms ──
    REQUEST_LATENCY = Histogram(
        "arki_request_duration_seconds",
        "AI request latency in seconds",
        ["provider"],
        buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
        registry=_REGISTRY,
    )
    RESPONSE_TOKENS = Histogram(
        "arki_response_tokens",
        "Response token count",
        ["provider", "model"],
        buckets=[10, 50, 100, 500, 1000, 5000, 10000, 50000],
        registry=_REGISTRY,
    )

    # ── Gauges ──
    ACTIVE_USERS = Gauge(
        "arki_active_users",
        "Currently active users",
        registry=_REGISTRY,
    )
    CIRCUIT_STATE = Gauge(
        "arki_circuit_breaker_state",
        "Circuit breaker state (0=closed, 1=half_open, 2=open)",
        ["provider"],
        registry=_REGISTRY,
    )
    UPTIME = Gauge(
        "arki_uptime_seconds",
        "Bot uptime in seconds",
        registry=_REGISTRY,
    )
    MEMORY_MB = Gauge(
        "arki_memory_usage_mb",
        "Process memory usage in MB",
        registry=_REGISTRY,
    )

    # ── Info ──
    BUILD_INFO = Info(
        "arki_build",
        "Build information",
        registry=_REGISTRY,
    )

except ImportError:
    _NATIVE = False
    _REGISTRY = None
    logger.debug("prometheus_client not installed — using built-in text exporter")


# ── Built-in fallback metrics store ──
class _MetricStore:
    """Lightweight metrics store when prometheus_client is unavailable."""

    def __init__(self) -> None:
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._info: Dict[str, Dict[str, str]] = {}

    def inc_counter(self, name: str, labels: Dict[str, str], value: float = 1.0) -> Any:
        key = f"{name}{{{self._fmt(labels)}}}"
        self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(self, name: str, labels: Dict[str, str], value: float) -> None:
        key = f"{name}{{{self._fmt(labels)}}}" if labels else name
        self._gauges[key] = value

    def observe_histogram(self, name: str, labels: Dict[str, str], value: float) -> Any:
        key = f"{name}{{{self._fmt(labels)}}}"
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)
        # Keep only last 10000
        if len(self._histograms[key]) > 10000:
            self._histograms[key] = self._histograms[key][-5000:]

    def set_info(self, name: str, info: Dict[str, str]) -> None:
        self._info[name] = info

    def _fmt(self, labels: Dict[str, str]) -> str:
        return ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))

    def to_prometheus_text(self) -> str:
        """Export in Prometheus text exposition format."""
        lines: List[str] = []

        # Counters
        for key, val in sorted(self._counters.items()):
            name = key.split("{")[0]
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{key} {val}")

        # Gauges
        for key, val in sorted(self._gauges.items()):
            name = key.split("{")[0] if "{" in key else key
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{key} {val}")

        # Histograms (simplified: export sum, count, quantiles)
        seen = set()
        for key, values in sorted(self._histograms.items()):
            name = key.split("{")[0]
            if name not in seen:
                lines.append(f"# TYPE {name} histogram")
                seen.add(name)
            n = len(values)
            s = sum(values)
            # Build histogram lines (avoid complex f-string nesting)
            base = key.replace("}", "")
            lbl = key.split("{")[1] if "{" in key else ""
            lines.append(base + ',le="+Inf"} ' + str(n))
            lines.append(name + "_count{" + lbl + " " + str(n))
            lines.append(name + "_sum{" + lbl + " " + format(s, ".4f"))

        # Info
        for name, info in self._info.items():
            labels = ",".join(f'{k}="{v}"' for k, v in info.items())
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name}{{{labels}}} 1")

        return "\n".join(lines) + "\n"

_store = _MetricStore()
_boot_time = time.time()


# ── Public API (works with or without prometheus_client) ──

def record_request(provider: str, model: str, status: str, latency_s: float, tokens: int = 0) -> Any:
    """Record an AI API request."""
    if _NATIVE:
        REQUEST_TOTAL.labels(provider=provider, model=model, status=status).inc()
        REQUEST_LATENCY.labels(provider=provider).observe(latency_s)
        if tokens > 0:
            RESPONSE_TOKENS.labels(provider=provider, model=model).observe(tokens)
    else:
        _store.inc_counter("arki_requests_total", {"provider": provider, "model": model, "status": status})
        _store.observe_histogram("arki_request_duration_seconds", {"provider": provider}, latency_s)

def record_message(message_type: str) -> Any:
    """Record a processed message."""
    if _NATIVE:
        MESSAGES_TOTAL.labels(message_type=message_type).inc()
    else:
        _store.inc_counter("arki_messages_total", {"message_type": message_type})

def record_error(error_type: str, provider: str = "") -> Any:
    """Record an error."""
    if _NATIVE:
        ERRORS_TOTAL.labels(error_type=error_type, provider=provider).inc()
    else:
        _store.inc_counter("arki_errors_total", {"error_type": error_type, "provider": provider})

def set_active_users(count: int) -> None:
    """Update active user count."""
    if _NATIVE:
        ACTIVE_USERS.set(count)
    else:
        _store.set_gauge("arki_active_users", {}, count)

def set_circuit_state(provider: str, state_value: int) -> None:
    """Update circuit breaker state (0=closed, 1=half_open, 2=open)."""
    if _NATIVE:
        CIRCUIT_STATE.labels(provider=provider).set(state_value)
    else:
        _store.set_gauge("arki_circuit_breaker_state", {"provider": provider}, state_value)

def set_build_info(version: str, mode: str, python_version: str) -> None:
    """Set build info."""
    info = {"version": version, "mode": mode, "python_version": python_version}
    if _NATIVE:
        BUILD_INFO.info(info)
    else:
        _store.set_info("arki_build_info", info)

def update_system_metrics() -> None:
    """Update system-level metrics (call periodically)."""
    uptime = time.time() - _boot_time
    if _NATIVE:
        UPTIME.set(uptime)
        try:
            import resource
            mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # KB→MB on Linux
            MEMORY_MB.set(mem)
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)
    else:
        _store.set_gauge("arki_uptime_seconds", {}, uptime)

    # Update circuit breaker states
    try:
        from arki_project.utils.circuit_breaker import get_all_breaker_health
        for name, health in get_all_breaker_health().items():
            state_map = {"closed": 0, "half_open": 1, "open": 2}
            set_circuit_state(name, state_map.get(health["state"], -1))
    except Exception as _err:
        logger.warning("Suppressed error: %s", _err)


def generate_metrics() -> tuple[str, str]:
    """Generate Prometheus metrics output.

    Returns: (text_content, content_type)
    """
    update_system_metrics()
    if _NATIVE:
        return generate_latest(_REGISTRY).decode("utf-8"), CONTENT_TYPE_LATEST
    else:
        return _store.to_prometheus_text(), "text/plain; version=0.0.4; charset=utf-8"


def export_metrics_text() -> str:
    """v26.1: Export all metrics in Prometheus text format for /metrics endpoint."""
    if _NATIVE:
        return generate_latest(_REGISTRY).decode("utf-8")
    
    # Fallback: manual text format
    lines = []
    for name, counter in _fallback_counters.items():
        lines.append(f"# HELP {name} Counter metric")
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{name} {counter}")
    
    for name, gauge in _fallback_gauges.items():
        lines.append(f"# HELP {name} Gauge metric")
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name} {gauge}")
    
    return "\n".join(lines)


