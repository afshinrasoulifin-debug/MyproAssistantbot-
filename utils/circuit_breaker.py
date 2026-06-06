
from __future__ import annotations
from arki_project.exceptions import ResilienceError
"""
utils/circuit_breaker.py — Production Circuit Breaker v19.0
═══════════════════════════════════════════════════════════════
Enterprise circuit breaker with:
- 3-state machine: CLOSED → OPEN → HALF_OPEN → CLOSED
- Bulkhead pattern (concurrency limiter per provider)
- Retry budget (max % of requests that can be retries)
- Sliding window failure tracking
- Prometheus-compatible metrics export
- Health status aggregation
"""

import asyncio
import logging
import time
from collections import deque
from enum import Enum
from typing import Any, Callable, Deque, Dict

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Service down, reject fast
    HALF_OPEN = "half_open" # Testing recovery


class CircuitOpenError(Exception):
    """Raised when circuit is open and call is rejected."""
    pass


class BulkheadFullError(Exception):
    """Raised when too many concurrent calls to a service."""
    pass


class RetryBudgetExhaustedError(Exception):
    """Raised when retry budget for the window is exhausted."""
    pass


class CircuitBreaker:
    """Production-grade circuit breaker with sliding window tracking."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
        window_size: float = 60.0,       # sliding window in seconds
        max_concurrent: int = 50,          # bulkhead: max parallel calls
        retry_budget_pct: float = 20.0,    # max 20% of calls can be retries
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.window_size = window_size
        self.max_concurrent = max_concurrent
        self.retry_budget_pct = retry_budget_pct

        # State
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0

        # Sliding window for accurate failure rate
        self._call_log: Deque[tuple[float, bool]] = deque()  # (timestamp, success)

        # Bulkhead
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_calls = 0

        # Retry budget tracking
        self._retry_count_window = 0
        self._total_count_window = 0
        self._window_reset_time = time.time()

        # Metrics
        self._metrics = {
            "total_calls": 0,
            "total_successes": 0,
            "total_failures": 0,
            "total_rejected": 0,
            "total_timeouts": 0,
            "trips": 0,           # times circuit opened
            "recoveries": 0,      # times circuit recovered
            "last_call_time": 0.0,
            "last_failure_time": 0.0,
            "avg_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
        }
        self._latencies: Deque[float] = deque(maxlen=1000)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info("Circuit %s: OPEN → HALF_OPEN", self.name)
        return self._state

    def can_execute(self) -> bool:
        """Return True if the circuit allows a request (CLOSED or HALF_OPEN)."""
        return self.state != CircuitState.OPEN

    @property
    def failure_rate(self) -> float:
        """Current failure rate in sliding window."""
        self._prune_window()
        if not self._call_log:
            return 0.0
        failures = sum(1 for _, ok in self._call_log if not ok)
        return failures / len(self._call_log) * 100

    def _prune_window(self) -> Any:
        """Remove entries outside the sliding window."""
        cutoff = time.time() - self.window_size
        while self._call_log and self._call_log[0][0] < cutoff:
            self._call_log.popleft()

    def _check_retry_budget(self, is_retry: bool = False) -> bool:
        """Check if retry budget allows this call."""
        now = time.time()
        if now - self._window_reset_time > self.window_size:
            self._retry_count_window = 0
            self._total_count_window = 0
            self._window_reset_time = now
        self._total_count_window += 1
        if is_retry:
            self._retry_count_window += 1
            if self._total_count_window > 10:  # Only enforce after enough samples
                pct = (self._retry_count_window / self._total_count_window) * 100
                if pct > self.retry_budget_pct:
                    return False
        return True

    def record_success(self) -> Any:
        now = time.time()
        self._call_log.append((now, True))
        self._metrics["total_successes"] += 1
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                self._metrics["recoveries"] += 1
                logger.info("Circuit %s: HALF_OPEN → CLOSED (recovered)", self.name)
        else:
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> Any:
        now = time.time()
        self._call_log.append((now, False))
        self._failure_count += 1
        self._last_failure_time = now
        self._metrics["total_failures"] += 1
        self._metrics["last_failure_time"] = now
        if self._failure_count >= self.failure_threshold:
            if self._state != CircuitState.OPEN:
                self._metrics["trips"] += 1
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit %s: → OPEN (failures=%d, rate=%.1f%%)",
                self.name, self._failure_count, self.failure_rate,
            )

    async def call(
        self, func: Callable, *args,
        is_retry: bool = False, timeout: float = 30.0,
        **kwargs,
    ) -> Any:
        """Execute function with circuit breaker + bulkhead + retry budget."""
        state = self.state

        # Circuit open → fast reject
        if state == CircuitState.OPEN:
            self._metrics["total_rejected"] += 1
            raise CircuitOpenError(
                f"Circuit {self.name} is OPEN — service unavailable "
                f"(failures={self._failure_count}, recovery in "
                f"{self.recovery_timeout - (time.time() - self._last_failure_time):.0f}s)"
            )

        # Half-open → limited calls
        if state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls > self.half_open_max_calls:
                self._metrics["total_rejected"] += 1
                raise CircuitOpenError(f"Circuit {self.name} HALF_OPEN limit reached")

        # Retry budget check
        if not self._check_retry_budget(is_retry):
            self._metrics["total_rejected"] += 1
            raise RetryBudgetExhaustedError(
                f"Circuit {self.name}: retry budget exhausted "
                f"({self.retry_budget_pct}% limit)"
            )

        # Bulkhead: limit concurrent calls
        acquired = self._semaphore._value > 0
        if not acquired and self._active_calls >= self.max_concurrent:
            self._metrics["total_rejected"] += 1
            raise BulkheadFullError(
                f"Circuit {self.name}: bulkhead full ({self.max_concurrent} concurrent)"
            )

        self._active_calls += 1
        self._metrics["total_calls"] += 1
        self._metrics["last_call_time"] = time.time()
        start = time.monotonic()

        try:
            async with self._semaphore:
                if asyncio.iscoroutinefunction(func):
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                else:
                    result = func(*args, **kwargs)

            latency = (time.monotonic() - start) * 1000
            self._latencies.append(latency)
            self._update_latency_metrics()
            self.record_success()
            return result

        except asyncio.TimeoutError:
            self._metrics["total_timeouts"] += 1
            self.record_failure()
            raise
        except ResilienceError:
            self.record_failure()
            raise
        finally:
            self._active_calls -= 1

    def _update_latency_metrics(self) -> Any:
        if self._latencies:
            self._metrics["avg_latency_ms"] = sum(self._latencies) / len(self._latencies)
            sorted_l = sorted(self._latencies)
            idx = min(int(len(sorted_l) * 0.99), len(sorted_l) - 1)
            self._metrics["p99_latency_ms"] = sorted_l[idx]

    def get_health(self) -> Dict[str, Any]:
        """Get health status for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_rate": round(self.failure_rate, 1),
            "active_calls": self._active_calls,
            "max_concurrent": self.max_concurrent,
            "metrics": dict(self._metrics),
        }

    def reset(self) -> Any:
        """Manual reset (admin action)."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._call_log.clear()
        logger.info("Circuit %s: manually RESET", self.name)


# ── Global Circuit Breaker Registry ──

_breaker_registry: Dict[str, CircuitBreaker] = {}


def get_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get or create a named circuit breaker."""
    if name not in _breaker_registry:
        _breaker_registry[name] = CircuitBreaker(name, **kwargs)
    return _breaker_registry[name]

def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Alias for get_breaker."""
    return get_breaker(name, **kwargs)


def get_all_breaker_health() -> Dict[str, Dict]:
    """Get health for all registered breakers."""
    return {name: cb.get_health() for name, cb in _breaker_registry.items()}


def reset_breaker(name: str) -> bool:
    """Reset a specific breaker."""
    if name in _breaker_registry:
        _breaker_registry[name].reset()
        return True
    return False


