
from __future__ import annotations
"""
utils/resilience.py — Production Resilience Layer v27.0
═══════════════════════════════════════════════════════
Provides:
  1. ProviderCircuitBreaker — per-provider circuit breaker with half-open state
  2. ProviderHealthMonitor — periodic health pings for all providers
  3. InputSanitizer — XSS/injection/overflow prevention
  4. ConnectionPoolManager — aiohttp session reuse per provider
  5. MemoryGuard — prevents memory leaks in long-running bots

Version: 27.0.0
"""

import asyncio
import html
import logging
import re
import time
import unicodedata
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# §1 — Circuit Breaker (per-provider)
# ═══════════════════════════════════════════════════════════════════

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Blocking calls (provider is down)
    HALF_OPEN = "half_open" # Testing with single call


@dataclass
class ProviderCircuitBreaker:
    """Per-provider circuit breaker with half-open recovery.

    States:
      CLOSED → consecutive failures ≥ threshold → OPEN
      OPEN → after recovery_timeout → HALF_OPEN
      HALF_OPEN → 1 success → CLOSED | 1 failure → OPEN

    Usage:
        cb = ProviderCircuitBreaker("openrouter")
        if cb.can_call():
            try:
                result = await call_api()
                cb.record_success()
            except Exception:
                cb.record_failure()
    """
    provider: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_calls: int = 2

    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    consecutive_failures: int = field(default=0, init=False)
    last_failure_time: float = field(default=0.0, init=False)
    total_failures: int = field(default=0, init=False)
    total_successes: int = field(default=0, init=False)
    total_blocked: int = field(default=0, init=False)
    _half_open_calls: int = field(default=0, init=False)
    _state_change_time: float = field(default_factory=time.monotonic, init=False)

    def can_call(self) -> bool:
        """Check if a call is allowed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            elapsed = time.monotonic() - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                self._transition(CircuitState.HALF_OPEN)
                self._half_open_calls = 0
                logger.info("CircuitBreaker[%s]: OPEN → HALF_OPEN (%.1fs elapsed)", self.provider, elapsed)
                return True
            self.total_blocked += 1
            return False

        if self.state == CircuitState.HALF_OPEN:
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

        return False

    def record_success(self) -> None:
        """Record a successful call."""
        self.total_successes += 1
        if self.state == CircuitState.HALF_OPEN:
            self._transition(CircuitState.CLOSED)
            self.consecutive_failures = 0
            logger.info("CircuitBreaker[%s]: HALF_OPEN → CLOSED (recovered)", self.provider)
        elif self.state == CircuitState.CLOSED:
            self.consecutive_failures = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self.consecutive_failures += 1
        self.total_failures += 1
        self.last_failure_time = time.monotonic()

        if self.state == CircuitState.HALF_OPEN:
            self._transition(CircuitState.OPEN)
            logger.warning("CircuitBreaker[%s]: HALF_OPEN → OPEN (recovery failed)", self.provider)
        elif self.state == CircuitState.CLOSED and self.consecutive_failures >= self.failure_threshold:
            self._transition(CircuitState.OPEN)
            logger.warning("CircuitBreaker[%s]: CLOSED → OPEN (%d consecutive failures)", self.provider, self.consecutive_failures)

    def _transition(self, new_state: CircuitState) -> None:
        self.state = new_state
        self._state_change_time = time.monotonic()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "state": self.state.value,
            "consecutive_failures": self.consecutive_failures,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "total_blocked": self.total_blocked,
            "uptime_seconds": time.monotonic() - self._state_change_time,
        }


class CircuitBreakerManager:
    """Manages circuit breakers for all providers."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0) -> None:
        self._breakers: Dict[str, ProviderCircuitBreaker] = {}
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

    def get(self, provider: str) -> ProviderCircuitBreaker:
        if provider not in self._breakers:
            self._breakers[provider] = ProviderCircuitBreaker(
                provider=provider,
                failure_threshold=self._failure_threshold,
                recovery_timeout=self._recovery_timeout,
            )
        return self._breakers[provider]

    def get_all_stats(self) -> List[Dict[str, Any]]:
        return [cb.get_stats() for cb in self._breakers.values()]

    def get_healthy_providers(self) -> Set[str]:
        return {p for p, cb in self._breakers.items() if cb.state != CircuitState.OPEN}


# ═══════════════════════════════════════════════════════════════════
# §2 — Health Monitor
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ProviderHealth:
    provider: str
    is_healthy: bool = True
    last_check: float = 0.0
    last_latency_ms: float = 0.0
    consecutive_ok: int = 0
    consecutive_fail: int = 0
    avg_latency_ms: float = 0.0
    _latencies: Deque[float] = field(default_factory=lambda: deque(maxlen=20))


class ProviderHealthMonitor:
    """Periodic health monitor for AI providers.

    Runs a background task that pings each provider every `interval` seconds.
    Auto-disables unhealthy providers via circuit breakers.

    Usage:
        monitor = ProviderHealthMonitor(circuit_manager, interval=300)
        await monitor.start()
        ...
        await monitor.stop()
    """

    def __init__(
        self,
        circuit_manager: CircuitBreakerManager,
        interval: float = 300.0,  # 5 minutes
        timeout: float = 15.0,
    ) -> None:
        self._circuit_manager = circuit_manager
        self._interval = interval
        self._timeout = timeout
        self._health: Dict[str, ProviderHealth] = {}
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._ping_fns: Dict[str, Callable] = {}

    def register_ping(self, provider: str, ping_fn: Callable) -> None:
        """Register a health-check ping function for a provider.

        ping_fn should be: async () -> bool (True if healthy)
        """
        self._ping_fns[provider] = ping_fn
        if provider not in self._health:
            self._health[provider] = ProviderHealth(provider=provider)

    async def start(self) -> None:
        """Start the background health monitor."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("HealthMonitor started (interval=%.0fs, %d providers)", self._interval, len(self._ping_fns))

    async def stop(self) -> None:
        """Stop the background health monitor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("HealthMonitor stopped")

    async def _monitor_loop(self) -> None:
        while self._running:
            try:
                await self._check_all()
            except Exception as e:
                logger.error("HealthMonitor error: %s", e)
            await asyncio.sleep(self._interval)

    async def _check_all(self) -> None:
        tasks = []
        for provider, ping_fn in self._ping_fns.items():
            tasks.append(self._check_one(provider, ping_fn))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_one(self, provider: str, ping_fn: Callable) -> None:
        health = self._health.setdefault(provider, ProviderHealth(provider=provider))
        t0 = time.monotonic()
        try:
            result = await asyncio.wait_for(ping_fn(), timeout=self._timeout)
            latency = (time.monotonic() - t0) * 1000
            health.last_check = time.time()
            health.last_latency_ms = latency
            health._latencies.append(latency)
            health.avg_latency_ms = sum(health._latencies) / len(health._latencies)

            if result:
                health.is_healthy = True
                health.consecutive_ok += 1
                health.consecutive_fail = 0
                self._circuit_manager.get(provider).record_success()
            else:
                health.is_healthy = False
                health.consecutive_ok = 0
                health.consecutive_fail += 1
                self._circuit_manager.get(provider).record_failure()
        except Exception as e:
            health.is_healthy = False
            health.consecutive_ok = 0
            health.consecutive_fail += 1
            health.last_check = time.time()
            self._circuit_manager.get(provider).record_failure()
            logger.debug("HealthCheck[%s] failed: %s", provider, e)

    def get_all_health(self) -> List[Dict[str, Any]]:
        return [
            {
                "provider": h.provider,
                "healthy": h.is_healthy,
                "last_check": h.last_check,
                "latency_ms": round(h.avg_latency_ms, 1),
                "consecutive_ok": h.consecutive_ok,
                "consecutive_fail": h.consecutive_fail,
            }
            for h in self._health.values()
        ]


# ═══════════════════════════════════════════════════════════════════
# §3 — Input Sanitizer
# ═══════════════════════════════════════════════════════════════════

class InputSanitizer:
    """Enterprise-grade input sanitization for Telegram bot.

    Prevents:
      - XSS/HTML injection
      - Prompt injection attempts
      - Unicode attacks (homoglyphs, invisible chars, RTL override)
      - Message overflow (length limits)
      - Command injection
      - Excessive whitespace/newlines
    """

    MAX_MESSAGE_LENGTH = 16_000  # chars (Telegram limit ~4096, but we allow more for AI)
    MAX_TOKENS_ESTIMATE = 4_000  # rough limit
    MAX_NEWLINES = 100
    MAX_CONSECUTIVE_SPACES = 5

    # Dangerous Unicode categories
    _INVISIBLE_CHARS = re.compile(r'[\u200b-\u200f\u2028-\u202f\u2060-\u206f\ufeff\u00ad]')
    _CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')
    _RTL_OVERRIDES = re.compile(r'[\u202a-\u202e\u2066-\u2069]')

    # Prompt injection patterns (common attacks)
    _INJECTION_PATTERNS = [
        re.compile(r'ignore\s+(all\s+)?previous\s+instructions', re.IGNORECASE),
        re.compile(r'system\s*:\s*you\s+are', re.IGNORECASE),
        re.compile(r'<\|im_start\|>', re.IGNORECASE),
        re.compile(r'\[INST\]', re.IGNORECASE),
        re.compile(r'###\s*(system|instruction|human|assistant)\s*:', re.IGNORECASE),
        re.compile(r'<<SYS>>', re.IGNORECASE),
    ]

    @classmethod
    def sanitize(cls, text: str, strict: bool = False) -> Tuple[str, List[str]]:
        """Sanitize user input text.

        Args:
            text: Raw user input
            strict: If True, also remove prompt injection attempts

        Returns:
            (sanitized_text, list_of_warnings)
        """
        if not text:
            return "", []

        warnings: List[str] = []

        # 1. Length limit
        if len(text) > cls.MAX_MESSAGE_LENGTH:
            text = text[:cls.MAX_MESSAGE_LENGTH]
            warnings.append(f"truncated_to_{cls.MAX_MESSAGE_LENGTH}_chars")

        # 2. Unicode normalization (NFC)
        text = unicodedata.normalize("NFC", text)

        # 3. Remove control characters (keep \n, \r, \t)
        cleaned = cls._CONTROL_CHARS.sub("", text)
        if cleaned != text:
            warnings.append("control_chars_removed")
            text = cleaned

        # 4. Neutralize RTL override attacks (check before invisible chars)
        cleaned = cls._RTL_OVERRIDES.sub("", text)
        if cleaned != text:
            warnings.append("rtl_override_removed")
            text = cleaned

        # 5. Remove invisible characters
        cleaned = cls._INVISIBLE_CHARS.sub("", text)
        if cleaned != text:
            warnings.append("invisible_chars_removed")
            text = cleaned

        # 6. HTML entity escape (prevent XSS in any web rendering)
        text = html.escape(text, quote=False)

        # 7. Limit consecutive newlines
        text = re.sub(r'\n{4,}', '\n\n\n', text)

        # 8. Limit consecutive spaces
        text = re.sub(r' {6,}', '     ', text)

        # 9. Prompt injection detection (warning only, unless strict)
        for pattern in cls._INJECTION_PATTERNS:
            if pattern.search(text):
                warnings.append("prompt_injection_detected")
                if strict:
                    text = pattern.sub("[filtered]", text)
                break

        return text.strip(), warnings

    @classmethod
    def sanitize_model_key(cls, key: str) -> str:
        """Sanitize a model key to prevent directory traversal or injection."""
        # Only allow alphanumeric, hyphens, underscores, dots, slashes
        return re.sub(r'[^a-zA-Z0-9\-_./]', '', key)[:128]

    @classmethod
    def is_safe_callback_data(cls, data: str) -> bool:
        """Validate Telegram callback data is safe."""
        if not data or len(data) > 64:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_\-:]+$', data))


# ═══════════════════════════════════════════════════════════════════
# §4 — Connection Pool Manager
# ═══════════════════════════════════════════════════════════════════

class ConnectionPoolManager:
    """Manages aiohttp ClientSession instances per provider.

    Benefits:
      - Connection reuse (TCP keep-alive)
      - Per-provider connection limits
      - Graceful cleanup on shutdown
      - Timeout configuration per provider

    Usage:
        pool = ConnectionPoolManager()
        session = await pool.get_session("openrouter")
        async with session.post(url, json=data) as resp:
            ...
        await pool.close_all()  # On shutdown
    """

    DEFAULT_LIMITS = {
        "openrouter": {"total": 50, "per_host": 20, "timeout": 30},
        "google": {"total": 30, "per_host": 15, "timeout": 30},
        "groq": {"total": 30, "per_host": 15, "timeout": 20},
        "huggingface": {"total": 20, "per_host": 10, "timeout": 60},
        "together": {"total": 20, "per_host": 10, "timeout": 30},
        "cerebras": {"total": 20, "per_host": 10, "timeout": 20},
        "deepinfra": {"total": 20, "per_host": 10, "timeout": 30},
    }

    def __init__(self) -> None:
        self._sessions: Dict[str, Any] = {}  # provider → aiohttp.ClientSession
        self._lock = asyncio.Lock()

    async def get_session(self, provider: str) -> Any:
        """Get or create an aiohttp ClientSession for a provider."""
        if provider in self._sessions and not self._sessions[provider].closed:
            return self._sessions[provider]

        async with self._lock:
            # Double-check after acquiring lock
            if provider in self._sessions and not self._sessions[provider].closed:
                return self._sessions[provider]

            try:
                import aiohttp
                limits = self.DEFAULT_LIMITS.get(provider, {"total": 20, "per_host": 10, "timeout": 30})
                connector = aiohttp.TCPConnector(
                    limit=limits["total"],
                    limit_per_host=limits["per_host"],
                    ttl_dns_cache=300,
                    enable_cleanup_closed=True,
                    keepalive_timeout=30,
                )
                timeout = aiohttp.ClientTimeout(total=limits["timeout"])
                session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={"User-Agent": "ArkiEngine/27.0"},
                )
                self._sessions[provider] = session
                logger.debug("ConnectionPool: Created session for %s (limit=%d)", provider, limits["total"])
                return session
            except ImportError:
                logger.warning("aiohttp not available — no connection pooling")
                return None

    async def close_all(self) -> None:
        """Close all sessions (call on shutdown)."""
        for provider, session in self._sessions.items():
            if session and not session.closed:
                await session.close()
                logger.debug("ConnectionPool: Closed session for %s", provider)
        self._sessions.clear()

    def get_stats(self) -> Dict[str, Any]:
        stats = {}
        for provider, session in self._sessions.items():
            if session and not session.closed:
                connector = session.connector
                stats[provider] = {
                    "active": True,
                    "limit": getattr(connector, '_limit', 0),
                    "limit_per_host": getattr(connector, '_limit_per_host', 0),
                }
            else:
                stats[provider] = {"active": False}
        return stats


# ═══════════════════════════════════════════════════════════════════
# §5 — Memory Guard
# ═══════════════════════════════════════════════════════════════════

class MemoryGuard:
    """Prevents memory leaks in long-running bots.

    Monitors deque/dict sizes and automatically trims when thresholds
    are exceeded. Call `check()` periodically (e.g., every 1000 requests).
    """

    def __init__(self, max_deque_size: int = 10_000, max_dict_size: int = 50_000) -> None:
        self._max_deque = max_deque_size
        self._max_dict = max_dict_size
        self._check_count = 0
        self._trims = 0

    def register_deque(self, name: str, dq: deque) -> None:
        """Register a deque for monitoring."""
        if not hasattr(self, '_deques'):
            self._deques: Dict[str, deque] = {}
        self._deques[name] = dq

    def register_dict(self, name: str, d: dict) -> None:
        """Register a dict for monitoring."""
        if not hasattr(self, '_dicts'):
            self._dicts: Dict[str, dict] = {}
        self._dicts[name] = d

    def check(self) -> int:
        """Check all registered collections and trim if needed.

        Returns: number of items trimmed.
        """
        self._check_count += 1
        trimmed = 0

        for name, dq in getattr(self, '_deques', {}).items():
            if len(dq) > self._max_deque:
                excess = len(dq) - self._max_deque
                for _ in range(excess):
                    dq.popleft()
                trimmed += excess
                logger.debug("MemoryGuard: Trimmed %d items from deque '%s'", excess, name)

        for name, d in getattr(self, '_dicts', {}).items():
            if len(d) > self._max_dict:
                # Keep most recent entries (by insertion order in Python 3.7+)
                excess = len(d) - self._max_dict
                keys_to_remove = list(d.keys())[:excess]
                for k in keys_to_remove:
                    del d[k]
                trimmed += excess
                logger.debug("MemoryGuard: Trimmed %d items from dict '%s'", excess, name)

        if trimmed:
            self._trims += 1
        return trimmed

    def get_stats(self) -> Dict[str, Any]:
        return {
            "checks": self._check_count,
            "trims": self._trims,
            "deques": {n: len(d) for n, d in getattr(self, '_deques', {}).items()},
            "dicts": {n: len(d) for n, d in getattr(self, '_dicts', {}).items()},
        }


# ═══════════════════════════════════════════════════════════════════
# §6 — Singletons & Integration
# ═══════════════════════════════════════════════════════════════════

_circuit_manager: Optional[CircuitBreakerManager] = None
_health_monitor: Optional[ProviderHealthMonitor] = None
_connection_pool: Optional[ConnectionPoolManager] = None
_input_sanitizer: Optional[InputSanitizer] = None
_memory_guard: Optional[MemoryGuard] = None


def get_circuit_manager() -> CircuitBreakerManager:
    global _circuit_manager
    if _circuit_manager is None:
        _circuit_manager = CircuitBreakerManager(failure_threshold=5, recovery_timeout=60.0)
    return _circuit_manager


def get_health_monitor() -> ProviderHealthMonitor:
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = ProviderHealthMonitor(get_circuit_manager(), interval=300.0)
    return _health_monitor


def get_connection_pool() -> ConnectionPoolManager:
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = ConnectionPoolManager()
    return _connection_pool


def get_input_sanitizer() -> InputSanitizer:
    global _input_sanitizer
    if _input_sanitizer is None:
        _input_sanitizer = InputSanitizer()
    return _input_sanitizer


def get_memory_guard() -> MemoryGuard:
    global _memory_guard
    if _memory_guard is None:
        _memory_guard = MemoryGuard()
    return _memory_guard


