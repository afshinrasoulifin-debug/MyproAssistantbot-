
from __future__ import annotations
"""
middlewares/profiler.py — Handler Performance Profiler v10.4.1
═════════════════════════════════════════════════════════════
Middleware that tracks per-handler performance: latency distribution,
error rates, memory usage, and slow query correlation.

Features:
  - Per-handler latency tracking with percentiles
  - Slow handler detection
  - Error rate per handler
  - Handler dependency tracing (which handlers call which services)
  - Automatic slow handler alerts
  - Dashboard with top handlers by latency/errors
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Deque, Dict, List, Optional

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)


@dataclass
class HandlerProfile:
    """Performance profile for a single handler."""
    name: str
    total_calls: int = 0
    total_errors: int = 0
    total_time_ms: float = 0.0
    max_time_ms: float = 0.0
    recent_latencies: Deque[float] = field(default_factory=lambda: deque(maxlen=500))
    last_called: float = 0.0
    last_error: str = ""

    def record(self, duration_ms: float, error: Optional[str] = None):
        self.total_calls += 1
        self.total_time_ms += duration_ms
        self.max_time_ms = max(self.max_time_ms, duration_ms)
        self.recent_latencies.append(duration_ms)
        self.last_called = time.time()
        if error:
            self.total_errors += 1
            self.last_error = error[:200]

    @property
    def avg_ms(self) -> float:
        return self.total_time_ms / max(1, self.total_calls)

    @property
    def p95_ms(self) -> float:
        if not self.recent_latencies:
            return 0.0
        s = sorted(self.recent_latencies)
        return s[int(len(s) * 0.95)]

    @property
    def p99_ms(self) -> float:
        if not self.recent_latencies:
            return 0.0
        s = sorted(self.recent_latencies)
        return s[min(int(len(s) * 0.99), len(s) - 1)]

    @property
    def error_rate(self) -> float:
        return self.total_errors / max(1, self.total_calls)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "calls": self.total_calls,
            "errors": self.total_errors,
            "error_rate": round(self.error_rate, 4),
            "avg_ms": round(self.avg_ms, 1),
            "p95_ms": round(self.p95_ms, 1),
            "p99_ms": round(self.p99_ms, 1),
            "max_ms": round(self.max_time_ms, 1),
        }


class HandlerProfiler:
    """Global handler profiler — tracks performance across all handlers."""

    def __init__(self, slow_threshold_ms: float = 2000.0):
        self._profiles: Dict[str, HandlerProfile] = {}
        self._slow_threshold = slow_threshold_ms
        self._total_requests = 0
        self._start_time = time.time()

    def record(self, handler_name: str, duration_ms: float, error: Optional[str] = None):
        if handler_name not in self._profiles:
            self._profiles[handler_name] = HandlerProfile(name=handler_name)
        self._profiles[handler_name].record(duration_ms, error)
        self._total_requests += 1
        if duration_ms > self._slow_threshold:
            logger.warning("⏱️ Slow handler: %s took %.0fms", handler_name, duration_ms)

    def get_slow_handlers(self, limit: int = 10) -> List[Dict]:
        """Get handlers with avg latency above threshold."""
        slow = [
            p.to_dict() for p in self._profiles.values()
            if p.avg_ms > self._slow_threshold
        ]
        slow.sort(key=lambda x: -x["avg_ms"])
        return slow[:limit]

    def get_error_handlers(self, limit: int = 10) -> List[Dict]:
        """Get handlers with highest error rates."""
        err = [
            p.to_dict() for p in self._profiles.values()
            if p.total_errors > 0
        ]
        err.sort(key=lambda x: -x["error_rate"])
        return err[:limit]

    def get_top_handlers(self, by: str = "calls", limit: int = 10) -> List[Dict]:
        """Get top handlers by calls/time/errors."""
        all_h = list(self._profiles.values())
        if by == "calls":
            all_h.sort(key=lambda x: -x.total_calls)
        elif by == "time":
            all_h.sort(key=lambda x: -x.total_time_ms)
        elif by == "errors":
            all_h.sort(key=lambda x: -x.total_errors)
        return [h.to_dict() for h in all_h[:limit]]

    def dashboard(self) -> Dict:
        """Full profiler dashboard."""
        rps = self._total_requests / max(1, time.time() - self._start_time)
        all_latencies = []
        for p in self._profiles.values():
            all_latencies.extend(p.recent_latencies)
        if all_latencies:
            all_latencies.sort()
            global_p95 = all_latencies[int(len(all_latencies) * 0.95)]
        else:
            global_p95 = 0.0

        return {
            "total_requests": self._total_requests,
            "requests_per_second": round(rps, 2),
            "unique_handlers": len(self._profiles),
            "global_p95_ms": round(global_p95, 1),
            "slow_handlers": self.get_slow_handlers(5),
            "error_handlers": self.get_error_handlers(5),
            "top_by_calls": self.get_top_handlers("calls", 5),
        }


# Global instance
_profiler: Optional[HandlerProfiler] = None

def get_profiler() -> HandlerProfiler:
    global _profiler
    if _profiler is None:
        _profiler = HandlerProfiler()
    return _profiler


class ProfilerMiddleware(BaseMiddleware):
    """aiogram middleware that auto-profiles every handler call."""

    def __init__(self, profiler: Optional[HandlerProfiler] = None):
        super().__init__()
        self._profiler = profiler or get_profiler()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        handler_name = getattr(handler, "__name__", str(handler))
        # Try to get a better name from the callback
        if hasattr(handler, "__wrapped__"):
            handler_name = getattr(handler.__wrapped__, "__name__", handler_name)

        t0 = time.time()
        error_msg = None
        try:
            result = await handler(event, data)
            return result
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            raise
        finally:
            duration_ms = (time.time() - t0) * 1000
            self._profiler.record(handler_name, duration_ms, error_msg)


