
"""
api_builder_pkg/rate_limiter.py — RateLimiter
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class RateLimiter:
    """Token bucket rate limiter per (user, model) pair.
    
    Limits:
      - Per-model RPM (requests per minute)
      - Per-user daily quota
      - Global burst protection
    """
    
    # Provider default limits
    PROVIDER_LIMITS = {
        "gemini":     {"rpm": 60,  "rpd": 1500},
        "groq":       {"rpm": 30,  "rpd": 14400},
        "openrouter": {"rpm": 20,  "rpd": 200},    # Free tier
        "openrouter_paid": {"rpm": 500, "rpd": 100000},  # Paid tier
    }
    
    def __init__(self):
        self._buckets: Dict[str, Dict] = {}  # (user_id, model_key) → bucket state
        self._global_count = 0
        self._global_window_start = time.time()
        self._global_rpm = 200  # Global burst limit
    
    def _get_bucket(self, user_id: str, model_key: str, provider: str) -> Dict:
        """Get or create token bucket for (user, model)."""
        key = f"{user_id}:{model_key}"
        if key not in self._buckets:
            limits = self.PROVIDER_LIMITS.get(provider, self.PROVIDER_LIMITS["openrouter"])
            self._buckets[key] = {
                "tokens": limits["rpm"],
                "max_tokens": limits["rpm"],
                "last_refill": time.time(),
                "refill_rate": limits["rpm"] / 60.0,  # tokens per second
                "daily_count": 0,
                "daily_limit": limits["rpd"],
                "daily_reset": time.time(),
            }
        return self._buckets[key]
    
    def check(self, user_id: str, model_key: str, provider: str) -> Tuple[bool, Optional[Dict]]:
        """Check if request is allowed.
        
        Returns:
            (allowed, info) — info contains retry_after_seconds if blocked.
        """
        bucket = self._get_bucket(user_id, model_key, provider)
        now = time.time()
        
        # Refill tokens
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(
            bucket["max_tokens"],
            bucket["tokens"] + elapsed * bucket["refill_rate"],
        )
        bucket["last_refill"] = now
        
        # Daily reset (24h)
        if now - bucket["daily_reset"] > 86400:
            bucket["daily_count"] = 0
            bucket["daily_reset"] = now
        
        # Global burst check
        if now - self._global_window_start > 60:
            self._global_count = 0
            self._global_window_start = now
        
        # Check limits
        if self._global_count >= self._global_rpm:
            retry_after = 60 - (now - self._global_window_start)
            return False, {"reason": "global_burst", "retry_after_seconds": max(1, int(retry_after))}
        
        if bucket["daily_count"] >= bucket["daily_limit"]:
            retry_after = 86400 - (now - bucket["daily_reset"])
            return False, {"reason": "daily_quota", "retry_after_seconds": max(1, int(retry_after))}
        
        if bucket["tokens"] < 1:
            retry_after = (1 - bucket["tokens"]) / bucket["refill_rate"]
            return False, {"reason": "rate_limit", "retry_after_seconds": max(1, int(retry_after))}
        
        # Consume
        bucket["tokens"] -= 1
        bucket["daily_count"] += 1
        self._global_count += 1
        
        return True, None
    
    def get_usage(self, user_id: str) -> Dict[str, Dict]:
        """Get usage stats for a user across all models."""
        result = {}
        for key, bucket in self._buckets.items():
            uid, model = key.split(":", 1)
            if uid == user_id:
                result[model] = {
                    "remaining_rpm": max(0, int(bucket["tokens"])),
                    "daily_used": bucket["daily_count"],
                    "daily_limit": bucket["daily_limit"],
                }
        return result


# ═══════════════════════════════════════════════════════════════════
# Auth Middleware — API key + tier-based access
# ═══════════════════════════════════════════════════════════════════



