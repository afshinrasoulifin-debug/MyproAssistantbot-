
from __future__ import annotations
"""
tg_bot/utils/titanium/rate_limiter.py — L5 Adaptive Rate Control v10.1
═══════════════════════════════════════════════════════════════════════════
Smart rate control — NOT a limiter. Monitors throughput but never blocks.

v10.1 changes:
  • Default: UNLIMITED (no artificial caps)
  • "Check" always returns True in unlimited mode (default)
  • Optional burst protection only for abuse prevention
  • Throughput metrics for monitoring
  • Per-key adaptive windows
  • No progressive blocking unless explicitly enabled

Ported from: TITANIUM ZKI security/environment_purge.ts (rate control part)
"""


import time
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict

logger = logging.getLogger("titanium.rate_limiter")

# ── Configuration ────────────────────────────────────────────

DEFAULT_MAX_REQUESTS = 0              # 0 = UNLIMITED (no cap)
DEFAULT_WINDOW_SECONDS = 60           # monitoring window only
CLEANUP_INTERVAL = 300                # purge old entries every 5 min
ABUSE_THRESHOLD = 1000                # absolute safety: 1000 req/min = abuse


@dataclass(slots=True)
class RateBucket:
    """A sliding window rate monitoring bucket."""
    timestamps: list = field(default_factory=list)
    blocked_until: float = 0.0
    total_served: int = 0


class TitaniumRateLimiter:
    """
    Adaptive rate controller.

    Default mode: UNLIMITED — check() always returns True.
    Metrics-only: tracks throughput for monitoring/dashboards.
    Abuse protection: optional hard cap (default 1000/min) for DDoS defense.

    Usage:
      limiter = get_rate_limiter()         # unlimited
      limiter.check("user:123")            # always True
      limiter.throughput("user:123")       # requests in current window
    """

    def __init__(
        self,
        max_requests: int = DEFAULT_MAX_REQUESTS,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        abuse_threshold: int = ABUSE_THRESHOLD,
    ) -> None:
        self.max_requests = max_requests  # 0 = unlimited
        self.window_seconds = window_seconds
        self.abuse_threshold = abuse_threshold
        self._buckets: Dict[str, RateBucket] = defaultdict(RateBucket)
        self._violations: Dict[str, int] = defaultdict(int)
        self._last_cleanup = time.monotonic()
        self._total_checks = 0
        self._total_blocked = 0

    def check(self, key: str) -> bool:
        """
        Check if a request is allowed.

        In unlimited mode (default): ALWAYS returns True.
        Only blocks on abuse threshold (1000 req/min).
        """
        now = time.monotonic()
        self._total_checks += 1
        self._maybe_cleanup(now)

        bucket = self._buckets[key]

        # Sliding window: remove expired timestamps
        cutoff = now - self.window_seconds
        bucket.timestamps = [t for t in bucket.timestamps if t > cutoff]

        current = len(bucket.timestamps)

        # Abuse protection only (very high threshold)
        if self.abuse_threshold > 0 and current >= self.abuse_threshold:
            self._total_blocked += 1
            logger.error(
                "ABUSE detected for %s (%d req/%.0fs) — temporarily blocked",
                key, current, self.window_seconds,
            )
            return False

        # Normal rate limiting (only if max_requests > 0)
        if self.max_requests > 0 and current >= self.max_requests:
            self._total_blocked += 1
            logger.debug(
                "Rate limit for %s (%d/%d in %.0fs)",
                key, current, self.max_requests, self.window_seconds,
            )
            return False

        # Allow + record
        bucket.timestamps.append(now)
        bucket.total_served += 1
        return True

    def throughput(self, key: str) -> int:
        """Current requests in window for monitoring."""
        now = time.monotonic()
        bucket = self._buckets.get(key)
        if not bucket:
            return 0
        cutoff = now - self.window_seconds
        return sum(1 for t in bucket.timestamps if t > cutoff)

    def remaining(self, key: str) -> int:
        """How many requests remain. Returns 999999 in unlimited mode."""
        if self.max_requests <= 0:
            return 999999
        return max(0, self.max_requests - self.throughput(key))

    def reset(self, key: str) -> None:
        """Reset for a key."""
        self._buckets.pop(key, None)
        self._violations.pop(key, None)

    def _maybe_cleanup(self, now: float) -> None:
        """Purge stale entries periodically."""
        if now - self._last_cleanup < CLEANUP_INTERVAL:
            return
        self._last_cleanup = now
        cutoff = now - self.window_seconds * 10

        to_remove = []
        for key, bucket in self._buckets.items():
            if not bucket.timestamps or bucket.timestamps[-1] < cutoff:
                to_remove.append(key)

        for key in to_remove:
            del self._buckets[key]
            self._violations.pop(key, None)

        if to_remove:
            logger.debug("Rate control cleanup: removed %d stale entries", len(to_remove))

    @property
    def stats(self) -> dict:
        """Current stats."""
        return {
            "mode": "unlimited" if self.max_requests <= 0 else f"limited:{self.max_requests}/window",
            "active_keys": len(self._buckets),
            "total_checks": self._total_checks,
            "total_blocked": self._total_blocked,
            "block_rate": f"{self._total_blocked / max(1, self._total_checks):.2%}",
            "abuse_threshold": self.abuse_threshold,
        }


# ── Singleton ────────────────────────────────────────────────

_instance: TitaniumRateLimiter | None = None


def get_rate_limiter(
    max_requests: int = DEFAULT_MAX_REQUESTS,
    window_seconds: float = DEFAULT_WINDOW_SECONDS,
) -> TitaniumRateLimiter:
    """Get singleton rate limiter. Default: UNLIMITED."""
    global _instance
    if _instance is None:
        _instance = TitaniumRateLimiter(max_requests, window_seconds)
    return _instance


