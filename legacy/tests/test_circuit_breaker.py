
"""Tests for circuit breaker."""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCircuitBreaker:
    def test_starts_closed(self):
        from arki_project.utils.circuit_breaker import CircuitBreaker, CircuitState
        cb = CircuitBreaker("test", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold(self):
        from arki_project.utils.circuit_breaker import CircuitBreaker, CircuitState
        cb = CircuitBreaker("test2", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_reduces_failures(self):
        from arki_project.utils.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker("test3", failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 1

    @pytest.mark.asyncio
    async def test_call_success(self):
        from arki_project.utils.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker("test4")
        async def my_func():
            return "ok"
        result = await cb.call(my_func)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_call_rejects_when_open(self):
        from arki_project.utils.circuit_breaker import CircuitBreaker, CircuitOpenError
        cb = CircuitBreaker("test5", failure_threshold=1)
        cb.record_failure()
        async def my_func():
            return "ok"
        with pytest.raises(CircuitOpenError):
            await cb.call(my_func)


