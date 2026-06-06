
"""
web_search_pkg/search_rate_limiter.py — SearchRateLimiter
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class SearchRateLimiter:
    """Per-engine rate limiting using token bucket algorithm."""

    def __init__(self) -> None:
        self.buckets: Dict[str, Dict[str, float]] = {}
        self.default_rate = 1.0   # requests per second
        self.default_burst = 5    # max burst size

    def configure(self, engine: SearchEngine,
                  rate: float, burst: int) -> None:
        """Configure rate limit for an engine."""
        self.buckets[engine.value] = {
            "rate": rate,
            "burst": float(burst),
            "tokens": float(burst),
            "last_refill": time.time(),
        }

    def acquire(self, engine: SearchEngine) -> float:
        """
        Acquire a token. Returns wait time in seconds.

        Returns 0 if token is immediately available.
        """
        key = engine.value
        if key not in self.buckets:
            self.buckets[key] = {
                "rate": self.default_rate,
                "burst": float(self.default_burst),
                "tokens": float(self.default_burst),
                "last_refill": time.time(),
            }

        bucket = self.buckets[key]
        now = time.time()

        # Refill tokens
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(
            bucket["burst"],
            bucket["tokens"] + elapsed * bucket["rate"],
        )
        bucket["last_refill"] = now

        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return 0.0

        # Need to wait
        wait = (1.0 - bucket["tokens"]) / bucket["rate"]
        return wait


# ═══════════════════════════════════════════════════════════════════
# LRU Cache
# ═══════════════════════════════════════════════════════════════════



