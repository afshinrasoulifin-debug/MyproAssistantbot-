
"""
Metrics Collector v9.1
Collects and exposes application metrics.
Compatible with Prometheus text format.
"""
import time
import logging
from typing import Dict, Optional, Any
from collections import defaultdict

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Application metrics collector.

    Tracks:
    - Counters (messages, errors, API calls)
    - Gauges (active users, queue size)
    - Histograms (response times, token usage)
    """

    def __init__(self) -> None:
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list] = defaultdict(list)
        self._start_time = time.time()

    def increment(self, name: str, value: int = 1, labels: Optional[Dict] = None) -> Any:
        """Increment a counter."""
        key = self._make_key(name, labels)
        self._counters[key] += value

    def gauge(self, name: str, value: float, labels: Optional[Dict] = None) -> Any:
        """Set a gauge value."""
        key = self._make_key(name, labels)
        self._gauges[key] = value

    def observe(self, name: str, value: float, labels: Optional[Dict] = None) -> Any:
        """Record a histogram observation."""
        key = self._make_key(name, labels)
        hist = self._histograms[key]
        hist.append(value)
        # Keep last 10000 observations
        if len(hist) > 10000:
            self._histograms[key] = hist[-5000:]

    def timer(self, name: str, labels: Optional[Dict] = None) -> Any:
        """Context manager for timing operations."""
        return _Timer(self, name, labels)

    def _make_key(self, name: str, labels: Optional[Dict]) -> str:
        if labels:
            label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name

    def get_all(self) -> dict:
        """Get all metrics as a dictionary."""
        result = {
            "uptime_seconds": time.time() - self._start_time,
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
        }
        # Add histogram summaries
        result["histograms"] = {}
        for name, values in self._histograms.items():
            if values:
                sorted_vals = sorted(values)
                n = len(sorted_vals)
                result["histograms"][name] = {
                    "count": n,
                    "sum": sum(sorted_vals),
                    "avg": sum(sorted_vals) / n,
                    "min": sorted_vals[0],
                    "max": sorted_vals[-1],
                    "p50": sorted_vals[n // 2],
                    "p95": sorted_vals[int(n * 0.95)],
                    "p99": sorted_vals[int(n * 0.99)],
                }
        return result

    def to_prometheus(self) -> str:
        """Export in Prometheus text format."""
        lines = []
        lines.append("# Arki Engine Metrics")
        lines.append(f"arki_uptime_seconds {time.time() - self._start_time:.1f}")

        for name, value in self._counters.items():
            lines.append(f"arki_{name} {value}")

        for name, value in self._gauges.items():
            lines.append(f"arki_{name} {value}")

        for name, values in self._histograms.items():
            if values:
                n = len(values)
                lines.append(f"arki_{name}_count {n}")
                lines.append(f"arki_{name}_sum {sum(values):.3f}")

        return "\n".join(lines) + "\n"


class _Timer:
    def __init__(self, collector: Any, name: str, labels: Any) -> None:
        self.collector = collector
        self.name = name
        self.labels = labels

    def __enter__(self) -> Any:
        self._start = time.time()
        return self

    def __exit__(self, *args) -> None:
        duration = time.time() - self._start
        self.collector.observe(self.name, duration, self.labels)


# Singleton
_collector: Optional[MetricsCollector] = None

def get_metrics() -> MetricsCollector:
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


