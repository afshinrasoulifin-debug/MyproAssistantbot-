
from __future__ import annotations
"""
Performance Tracker — Measure handler execution times and bottlenecks.

Usage:
    from performance_tracker import perf_tracker

    @perf_tracker.track("ai_response")
    async def get_ai_response(text):
        ...

    stats = perf_tracker.get_stats()
"""

import time
import functools
import logging
from collections import defaultdict
from contextlib import contextmanager
from typing import Callable, Any, Dict, List

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Track execution times for various operations."""

    def __init__(self, slow_threshold_ms: float = 2000) -> None:
        self.slow_threshold = slow_threshold_ms / 1000
        self._timings: Dict[str, List[float]] = defaultdict(list)
        self._counts: Dict[str, int] = defaultdict(int)
        self._errors: Dict[str, int] = defaultdict(int)
        self._max_history = 1000

    @contextmanager
    def measure(self, operation: str) -> Any:
        start = time.monotonic()
        try:
            yield
        except Exception:
            self._errors[operation] += 1
            raise
        finally:
            elapsed = time.monotonic() - start
            self._record(operation, elapsed)

    def track(self, operation: str) -> Any:
        """Decorator to track async function performance."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                start = time.monotonic()
                try:
                    result = await func(*args, **kwargs)
                    elapsed = time.monotonic() - start
                    self._record(operation, elapsed)
                    return result
                except Exception:
                    elapsed = time.monotonic() - start
                    self._record(operation, elapsed)
                    self._errors[operation] += 1
                    raise
            return wrapper
        return decorator

    def _record(self, operation: str, elapsed: float) -> Any:
        self._counts[operation] += 1
        self._timings[operation].append(elapsed)
        if len(self._timings[operation]) > self._max_history:
            self._timings[operation] = self._timings[operation][-self._max_history:]

        if elapsed > self.slow_threshold:
            logger.warning(
                "🐌 Slow: %s took %.1fms (threshold: %.0fms)",
                operation, elapsed * 1000, self.slow_threshold * 1000,
            )

    def get_stats(self, operation: str = None) -> Dict[str, Any]:
        if operation:
            return self._stats_for(operation)
        return {name: self._stats_for(name) for name in sorted(self._counts.keys())}

    def _stats_for(self, name: str) -> Dict[str, Any]:
        timings = self._timings.get(name, [])
        if not timings:
            return {"count": 0}
        sorted_t = sorted(timings)
        return {
            "count": self._counts[name],
            "errors": self._errors.get(name, 0),
            "avg_ms": round(sum(timings) / len(timings) * 1000, 1),
            "min_ms": round(sorted_t[0] * 1000, 1),
            "max_ms": round(sorted_t[-1] * 1000, 1),
            "p50_ms": round(sorted_t[len(sorted_t) // 2] * 1000, 1),
            "p95_ms": round(sorted_t[int(len(sorted_t) * 0.95)] * 1000, 1),
            "p99_ms": round(sorted_t[int(len(sorted_t) * 0.99)] * 1000, 1),
        }

    def get_slow_operations(self, threshold_ms: float = None) -> List[Dict]:
        threshold = (threshold_ms / 1000) if threshold_ms else self.slow_threshold
        slow = []
        for name, timings in self._timings.items():
            slow_count = sum(1 for t in timings if t > threshold)
            if slow_count > 0:
                slow.append({
                    "operation": name,
                    "slow_count": slow_count,
                    "total_count": self._counts[name],
                    "slow_pct": round(slow_count / len(timings) * 100, 1),
                    "avg_ms": round(sum(timings) / len(timings) * 1000, 1),
                })
        return sorted(slow, key=lambda x: x["slow_pct"], reverse=True)

    def reset(self) -> Any:
        self._timings.clear()
        self._counts.clear()
        self._errors.clear()


perf_tracker = PerformanceTracker()


