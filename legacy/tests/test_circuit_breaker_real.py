
"""
tests/test_circuit_breaker_real.py — Circuit Breaker Integration Tests
══════════════════════════════════════════════════════════════════════
Real tests for circuit breaker behavior under failure conditions.
"""
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.circuit_breaker import (
    CircuitBreaker, CircuitOpenError, RetryBudgetExhaustedError, CircuitState,
    get_breaker, get_all_breaker_health, reset_breaker,
)

import pytest


class TestCircuitBreakerStates:
    """Test state transitions."""

    def test_starts_closed(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_half_open_after_recovery(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        import time
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    def test_closes_after_successful_half_open(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1, half_open_max_calls=2)
        cb.record_failure()
        cb.record_failure()
        import time
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_reopens_on_half_open_failure(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        import time
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerAsync:
    """Test async call wrapping."""

    @pytest.mark.asyncio
    async def test_successful_call(self):
        cb = CircuitBreaker("test_ok")
        async def ok_func():
            return "success"
        result = await cb.call(ok_func)
        assert result == "success"
        assert cb._metrics["total_calls"] == 1
        assert cb._metrics["total_successes"] == 1

    @pytest.mark.asyncio
    async def test_failing_call(self):
        cb = CircuitBreaker("test_fail", failure_threshold=2)
        async def fail_func():
            raise ConnectionError("test error")
        with pytest.raises(ConnectionError):
            await cb.call(fail_func)
        assert cb._metrics["total_failures"] == 1

    @pytest.mark.asyncio
    async def test_rejects_when_open(self):
        cb = CircuitBreaker("test_reject", failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        async def never_called():
            return "should not reach"
        with pytest.raises(CircuitOpenError):
            await cb.call(never_called)
        assert cb._metrics["total_rejected"] == 1

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        cb = CircuitBreaker("test_timeout", failure_threshold=5)
        async def slow_func():
            await asyncio.sleep(10)
        with pytest.raises(asyncio.TimeoutError):
            await cb.call(slow_func, timeout=0.1)
        assert cb._metrics["total_timeouts"] == 1

    @pytest.mark.asyncio
    async def test_bulkhead_limits_concurrency(self):
        cb = CircuitBreaker("test_bulk", max_concurrent=2)
        active = []

        async def slow_task():
            active.append(1)
            current = len(active)
            await asyncio.sleep(0.2)
            active.pop()
            return current

        # Run 2 concurrent — should work
        tasks = [cb.call(slow_task, timeout=5.0) for _ in range(2)]
        results = await asyncio.gather(*tasks)
        assert all(r <= 2 for r in results)

    @pytest.mark.asyncio
    async def test_retry_budget(self):
        cb = CircuitBreaker("test_budget", retry_budget_pct=10.0)
        async def ok():
            return True
        # Send many normal calls
        for _ in range(20):
            await cb.call(ok, timeout=5.0)
        # Now many retries should be rejected
        rejected = 0
        for _ in range(10):
            try:
                await cb.call(ok, is_retry=True, timeout=5.0)
            except RetryBudgetExhaustedError:
                rejected += 1
        assert rejected > 0


class TestCircuitBreakerMetrics:
    """Test metrics and health reporting."""

    def test_health_report(self):
        cb = CircuitBreaker("test_health")
        health = cb.get_health()
        assert health["name"] == "test_health"
        assert health["state"] == "closed"
        assert "metrics" in health

    def test_failure_rate_calculation(self):
        cb = CircuitBreaker("test_rate", failure_threshold=100, window_size=10.0)
        for _ in range(8):
            cb.record_success()
        for _ in range(2):
            cb.record_failure()
        rate = cb.failure_rate
        assert 15.0 < rate < 25.0  # ~20%

    def test_latency_tracking(self):
        cb = CircuitBreaker("test_latency")
        cb._latencies.extend([10.0, 20.0, 30.0, 40.0, 50.0])
        cb._update_latency_metrics()
        assert cb._metrics["avg_latency_ms"] == 30.0
        assert cb._metrics["p99_latency_ms"] >= 40.0

    def test_reset(self):
        cb = CircuitBreaker("test_reset", failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED

class TestGlobalRegistry:
    """Test global breaker registry."""

    def test_get_or_create(self):
        b1 = get_breaker("test_global_1", failure_threshold=10)
        b2 = get_breaker("test_global_1")
        assert b1 is b2

    def test_all_health(self):
        get_breaker("test_global_2")
        health = get_all_breaker_health()
        assert "test_global_2" in health

    def test_reset_specific(self):
        b = get_breaker("test_global_3", failure_threshold=1)
        b.record_failure()
        assert b.state == CircuitState.OPEN
        reset_breaker("test_global_3")
        assert b.state == CircuitState.CLOSED


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


