
from __future__ import annotations
"""
tg_bot/utils/slo_tracker.py — SLO/SLA Tracking v9.3
Track Service Level Objectives and generate compliance reports.
"""
import logging
import time
from typing import Dict, List, Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class SLOTracker:
    """
    Track SLOs:
    - Response time P95 < 3s
    - Error rate < 1%
    - Uptime > 99.9%
    """

    def __init__(self) -> None:
        self._response_times: List[float] = []
        self._error_count = 0
        self._success_count = 0
        self._start_time = time.time()
        self._downtime_seconds = 0.0

    def record_response(self, latency_ms: float, success: bool) -> Any:
        self._response_times.append(latency_ms)
        if success:
            self._success_count += 1
        else:
            self._error_count += 1
        # Keep only last 10K
        if len(self._response_times) > 10000:
            self._response_times = self._response_times[-5000:]

    def record_downtime(self, seconds: float) -> Any:
        self._downtime_seconds += seconds

    def get_slo_report(self) -> Dict:
        total = self._success_count + self._error_count
        uptime_seconds = time.time() - self._start_time
        uptime_pct = ((uptime_seconds - self._downtime_seconds) / max(1, uptime_seconds)) * 100

        sorted_times = sorted(self._response_times) if self._response_times else [0]
        p95_idx = int(len(sorted_times) * 0.95)
        p95 = sorted_times[min(p95_idx, len(sorted_times) - 1)]

        error_rate = (self._error_count / max(1, total)) * 100

        return {
            "slos": {
                "response_p95_ms": {"target": 3000, "actual": round(p95, 1),
                                    "met": p95 < 3000},
                "error_rate_pct": {"target": 1.0, "actual": round(error_rate, 3),
                                   "met": error_rate < 1.0},
                "uptime_pct": {"target": 99.9, "actual": round(uptime_pct, 3),
                               "met": uptime_pct > 99.9},
            },
            "overall_compliance": all([p95 < 3000, error_rate < 1.0, uptime_pct > 99.9]),
            "total_requests": total,
            "uptime_hours": round(uptime_seconds / 3600, 1),
        }


_tracker = None

def get_slo_tracker() -> SLOTracker:
    global _tracker
    if _tracker is None:
        _tracker = SLOTracker()
    return _tracker


