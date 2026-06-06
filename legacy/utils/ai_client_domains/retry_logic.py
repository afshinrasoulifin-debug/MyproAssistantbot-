
from __future__ import annotations
"""
utils/ai_client_domains/retry_logic.py — Retry & Circuit Breaking
═══════════════════════════════════════════════════════════════════
Extracted retry, fallback, and circuit-breaking logic.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CircuitState:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-provider circuit breaker."""

    def __init__(self, provider: str, failure_threshold: int = 5,
                 recovery_timeout: float = 60.0, half_open_max: int = 2) -> None:
        self.provider = provider
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0

    @property
    def is_available(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        return True  # HALF_OPEN allows attempts

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit %s: CLOSED (recovered)", self.provider)
        else:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning("Circuit %s: OPEN after %d failures", self.provider, self.failure_count)


class RetryManager:
    """Manages retry logic with exponential backoff."""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
                 max_delay: float = 30.0, exponential_base: float = 2.0) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    async def execute(self, fn: Callable[..., Coroutine], *args, **kwargs) -> Any:
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = min(
                        self.base_delay * (self.exponential_base ** attempt),
                        self.max_delay,
                    )
                    logger.debug("Retry %d/%d after %.1fs: %s",
                               attempt + 1, self.max_retries, delay, e)
                    await asyncio.sleep(delay)
        raise last_error


async def with_retry(fn: Any, *args, max_retries=3, **kwargs) -> Any:
    """Convenience wrapper for RetryManager."""
    mgr = RetryManager(max_retries=max_retries)
    return await mgr.execute(fn, *args, **kwargs)


