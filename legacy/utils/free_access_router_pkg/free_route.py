
"""
free_access_router_pkg/free_route.py — FreeRoute
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class FreeRoute:
    """A single free access route for a model — with advanced telemetry."""
    method: FreeAccessMethod
    api_url: str
    model_id: str               # Model ID as the provider expects
    headers_template: Dict[str, str] = field(default_factory=dict)
    key_env_var: str = ""        # Env var for free key (if needed)
    rate_limit_rpm: int = 30     # Known rate limit
    max_tokens: int = 65536
    is_healthy: bool = True
    last_check: float = 0.0
    last_success: float = 0.0
    consecutive_failures: int = 0
    total_calls: int = 0
    total_successes: int = 0
    cooldown_until: float = 0.0  # Don't use before this timestamp
    fallback_model_key: str = "" # For SMART_FALLBACK: redirect to this key

    # ── Advanced telemetry ──
    _latencies: List[float] = field(default_factory=list, repr=False)
    _tokens_used_minute: int = 0
    _tokens_minute_start: float = 0.0
    _retry_count: int = 0
    _adaptive_score: float = 1.0

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return self.total_successes / self.total_calls

    @property
    def is_available(self) -> bool:
        """Check if route is healthy and not in cooldown."""
        if not self.is_healthy:
            return False
        if self.cooldown_until > time.time():
            return False
        return True

    @property
    def latency_p50(self) -> float:
        """Median latency in seconds."""
        if not self._latencies:
            return 5.0  # Default assumption
        s = sorted(self._latencies)
        return s[len(s) // 2]

    @property
    def latency_p95(self) -> float:
        """95th percentile latency."""
        if not self._latencies:
            return 15.0
        s = sorted(self._latencies)
        idx = min(int(len(s) * 0.95), len(s) - 1)
        return s[idx]

    @property
    def adaptive_score(self) -> float:
        """Composite score for adaptive routing.

        Higher is better. Combines:
        - Success rate (0-1)
        - Inverse latency (faster = higher)
        - Availability freshness
        - Rate limit headroom
        """
        now = time.time()

        # Success component (0-1)
        sr = self.success_rate
        if self.total_calls < 3:
            sr = 0.8  # Optimistic prior for untested routes

        # Latency component (0-1, lower latency = higher score)
        lat = max(self.latency_p50, 0.1)
        latency_score = 1.0 / (1.0 + lat / 5.0)  # 5s → 0.5, 1s → 0.83

        # Freshness (prefer recently successful routes)
        if self.last_success > 0:
            age = now - self.last_success
            freshness = math.exp(-age / 3600)  # Decays over 1 hour
        else:
            freshness = 0.5  # Neutral

        # Cooldown proximity penalty
        if self.cooldown_until > now:
            cooldown_score = 0.0
        elif self.cooldown_until > 0:
            cooldown_score = min(1.0, (now - self.cooldown_until) / 300)
        else:
            cooldown_score = 1.0

        self._adaptive_score = sr * latency_score * freshness * cooldown_score
        return self._adaptive_score

    def mark_success(self, latency: float = 0.0):
        """Record a successful call with optional latency measurement."""
        self.total_calls += 1
        self.total_successes += 1
        self.consecutive_failures = 0
        self.is_healthy = True
        self.last_success = time.time()
        self.cooldown_until = 0.0
        self._retry_count = 0
        if latency > 0:
            self._latencies.append(latency)
            # Keep last 50 measurements
            if len(self._latencies) > 50:
                self._latencies = self._latencies[-50:]

    def mark_failure(self):
        """Record a failed call with exponential cooldown."""
        self.total_calls += 1
        self.consecutive_failures += 1
        self._retry_count += 1
        if self.consecutive_failures >= 3:
            self.is_healthy = False
            # Exponential cooldown: 30s, 60s, 120s, max 600s
            cooldown = min(30 * (2 ** (self.consecutive_failures - 3)), 600)
            # Add jitter (±20%) to spread load
            jitter = cooldown * random.uniform(-0.2, 0.2)
            self.cooldown_until = time.time() + cooldown + jitter

    def mark_rate_limited(self):
        """Special handling for 429 — short cooldown, not unhealthy."""
        self.total_calls += 1
        # Rate limit cooldown: 60-120s (randomized to spread load)
        self.cooldown_until = time.time() + random.uniform(60, 120)

    def track_tokens(self, tokens: int):
        """Track tokens used for TPM (tokens per minute) accounting."""
        now = time.time()
        if now - self._tokens_minute_start > 60:
            self._tokens_used_minute = 0
            self._tokens_minute_start = now
        self._tokens_used_minute += tokens

    def reset_health(self):
        """Reset health for auto-recovery."""
        self.is_healthy = True
        self.consecutive_failures = 0
        self.cooldown_until = 0.0
        self._retry_count = 0


# ═══════════════════════════════════════════════════════════════════
# §2 — LRU Response Cache
# ═══════════════════════════════════════════════════════════════════



