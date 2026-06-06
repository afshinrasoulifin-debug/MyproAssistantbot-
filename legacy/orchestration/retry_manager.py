
from __future__ import annotations
"""
tg_bot/orchestration/retry_manager.py — Retry + Circuit Breaker + Failover
══════════════════════════════════════════════════════════════════════════
Handles all failure recovery:
  • Exponential backoff with jitter
  • Per-provider circuit breakers (CLOSED → OPEN → HALF_OPEN)
  • Cross-provider failover chains
  • Request buffering during outages

Patterns covered:
  - provider-federation + adaptive-routing + failover
  - orchestration-runtime + intelligent-retries + request-buffering
  - orchestration-runtime + distributed-failover
  - orchestration-runtime + adaptive-retries
"""

import asyncio
import logging
import time

try:
    from arki_project.utils.titanium.compat import secure_random as random  # v10.1: CSPRNG
except ImportError:
    import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .types import ProviderName, ProviderStatus

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config
    from arki_project.utils.titanium.crypto import secure_hex
except ImportError:
    pass
logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"       # Normal — requests flow through
    OPEN = "open"           # Tripped — requests are rejected
    HALF_OPEN = "half_open" # Testing — limited requests allowed


@dataclass
class CircuitBreaker:
    """Per-provider circuit breaker with configurable thresholds."""
    name: ProviderName
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max: int = 3

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    half_open_calls: int = 0
    last_failure_time: float = 0.0
    last_state_change: float = field(default_factory=time.monotonic)

    def can_execute(self) -> bool:
        """Check if a request is allowed through."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout elapsed
            if time.monotonic() - self.last_failure_time >= self.recovery_timeout:
                self._transition(CircuitState.HALF_OPEN)
                return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max
        return False

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max:
                self._transition(CircuitState.CLOSED)
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0  # Reset on success

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()

        if self.state == CircuitState.HALF_OPEN:
            self._transition(CircuitState.OPEN)
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._transition(CircuitState.OPEN)

    def _transition(self, new_state: CircuitState) -> None:
        old = self.state
        self.state = new_state
        self.last_state_change = time.monotonic()
        if new_state == CircuitState.CLOSED:
            self.failure_count = 0
            self.success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self.half_open_calls = 0
            self.success_count = 0
        logger.info(
            "Circuit breaker [%s]: %s → %s",
            self.name.value, old.value, new_state.value,
        )

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN


@dataclass(slots=True)
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 30.0
    jitter_factor: float = 0.3
    retry_on: tuple = (Exception,)  # Updated at boot to transient types only

    def __post_init__(self) -> None:
        """Auto-set retry_on to transient error types only."""
        try:
            from .core import RateLimitError, OverloadedError
            self.retry_on = (RateLimitError, OverloadedError, ConnectionError, TimeoutError)
        except ImportError:
            pass  # Keep default (Exception) if core not available


class RetryManager:
    """Manages retries, circuit breakers, and failover across providers.

    Usage:
        result = await retry_mgr.execute_with_retry(
            providers=[ProviderName.GEMINI, ProviderName.GROQ],
            call_fn=lambda provider: call_provider(provider, request),
        )
    """

    def __init__(self, config: Optional[RetryConfig] = None) -> None:
        self._config = config or RetryConfig()
        self._breakers: Dict[ProviderName, CircuitBreaker] = {}
        self._pending_buffer: List[tuple] = []  # Buffered requests during outages

    # ── Setup ──────────────────────────────────────────────

    def register_breaker(
        self,
        provider: ProviderName,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> None:
        """Register a circuit breaker for a provider."""
        self._breakers[provider] = CircuitBreaker(
            name=provider,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    # ── Core retry logic ───────────────────────────────────

    async def execute_with_retry(
        self,
        providers: List[ProviderName],
        call_fn: Callable[[ProviderName], Awaitable[Any]],
        on_success: Optional[Callable[[ProviderName], None]] = None,
        on_failure: Optional[Callable[[ProviderName, Exception], None]] = None,
    ) -> Any:
        """Execute a call with retry + failover across providers.

        Tries each provider in order. For each provider:
          1. Check circuit breaker
          2. Attempt call with exponential backoff
          3. On exhausted retries, move to next provider

        Args:
            providers: Ordered list of providers to try.
            call_fn: Async function that takes a provider and makes the call.
            on_success: Callback on success (for stats).
            on_failure: Callback on failure per provider (for stats).

        Raises:
            The last exception if all providers fail.
        """
        last_error: Optional[Exception] = None

        for provider in providers:
            breaker = self._breakers.get(provider)

            # Skip if circuit is open
            if breaker and not breaker.can_execute():
                logger.info(
                    "Retry: skipping %s (circuit OPEN)", provider.value,
                )
                continue

            # Try with retries
            try:
                result = await self._retry_single(
                    provider, call_fn, breaker,
                )
                if on_success:
                    on_success(provider)
                return result
            except Exception as exc:
                last_error = exc
                if on_failure:
                    on_failure(provider, exc)
                logger.warning(
                    "Retry: provider %s exhausted after retries: %s",
                    provider.value, exc,
                )
                continue

        # All providers failed
        raise last_error or RuntimeError("All providers failed")

    async def _retry_single(
        self,
        provider: ProviderName,
        call_fn: Callable[[ProviderName], Awaitable[Any]],
        breaker: Optional[CircuitBreaker],
    ) -> Any:
        """Retry a single provider with exponential backoff."""
        cfg = self._config
        last_error: Optional[Exception] = None

        for attempt in range(cfg.max_retries + 1):
            try:
                result = await call_fn(provider)
                if breaker:
                    breaker.record_success()
                return result
            except cfg.retry_on as exc:
                last_error = exc
                if breaker:
                    breaker.record_failure()

                if attempt < cfg.max_retries:
                    delay = self._backoff_delay(attempt)
                    logger.info(
                        "Retry %s attempt %d/%d failed (%s), backoff %.1fs",
                        provider.value, attempt + 1, cfg.max_retries + 1,
                        type(exc).__name__, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise

        raise last_error or RuntimeError("Unexpected retry exit")

    def _backoff_delay(self, attempt: int) -> float:
        """Exponential backoff with CSPRNG jitter (v10)."""
        cfg = self._config
        delay = min(cfg.base_delay * (2 ** attempt), cfg.max_delay)
        # v10: CSPRNG jitter instead of random.uniform
        try:
            from arki_project.utils.titanium.crypto import csprng_float
            jitter = csprng_float() * delay * cfg.jitter_factor
        except ImportError:
            jitter = random.uniform(0, delay * cfg.jitter_factor)
        return delay + jitter

    # ── Introspection ──────────────────────────────────────

    def get_breaker_states(self) -> Dict[str, Dict]:
        """Get circuit breaker states for all providers."""
        return {
            name.value: {
                "state": b.state.value,
                "failures": b.failure_count,
                "is_open": b.is_open,
                "last_failure": b.last_failure_time,
            }
            for name, b in self._breakers.items()
        }

    def get_provider_status(self, provider: ProviderName) -> ProviderStatus:
        """Get effective status of a provider."""
        breaker = self._breakers.get(provider)
        if not breaker:
            return ProviderStatus.HEALTHY
        if breaker.state == CircuitState.OPEN:
            return ProviderStatus.DOWN
        if breaker.state == CircuitState.HALF_OPEN:
            return ProviderStatus.DEGRADED
        return ProviderStatus.HEALTHY

    def reset_breaker(self, provider: ProviderName) -> None:
        """Manually reset a circuit breaker."""
        breaker = self._breakers.get(provider)
        if breaker:
            breaker._transition(CircuitState.CLOSED)


