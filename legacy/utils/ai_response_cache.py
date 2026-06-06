
from __future__ import annotations
"""
tg_bot/utils/ai_response_cache.py — AI Response Cache v9.4
Cache identical AI requests to reduce API costs and latency.
"""
import hashlib
import logging
import time
from typing import Dict, Optional, Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class AIResponseCache:
    """Cache AI responses based on prompt hash."""

    def __init__(self, max_size: int = 5000, default_ttl: float = 3600.0) -> None:
        self._cache: Dict[str, tuple] = {}  # hash -> (response, expires_at)
        self._quality_scores: Dict[str, float] = {}  # v26.2: hash -> quality_score
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def _hash(self, prompt: str, model: str, temperature: float) -> str:
        key = f"{model}:{temperature:.1f}:{prompt}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def get(self, prompt: str, model: str, temperature: float = 0.7) -> Optional[str]:
        """Get cached response if available."""
        h = self._hash(prompt, model, temperature)
        if h in self._cache:
            response, expires = self._cache[h]
            if time.time() < expires:
                self._hits += 1
                return response
            del self._cache[h]
        self._misses += 1
        return None

    def set(self, prompt: str, model: str, response: str,
            temperature: float = 0.7, ttl: float = None,
            quality_score: float = 0.0) -> Any:
        """Cache an AI response. v26.2: also stores quality_score."""
        # Don't cache very short or error responses
        if len(response) < 10:
            return
        h = self._hash(prompt, model, temperature)
        self._cache[h] = (response, time.time() + (ttl or self._default_ttl))
        if quality_score > 0:
            self._quality_scores[h] = quality_score

        # Evict oldest if too large
        if len(self._cache) > self._max_size:
            oldest = min(self._cache, key=lambda k: self._cache[k][1])
            self._quality_scores.pop(oldest, None)
            del self._cache[oldest]

    def invalidate_model(self, model: str) -> Any:
        """Invalidate all cached responses for a model."""
        keys_to_delete = [k for k, (_, _) in self._cache.items()]
        # Since hash doesn't contain model directly, clear all
        self._cache.clear()

    def get_quality(self, prompt: str, model: str, temperature: float = 0.7) -> float:
        """v26.2: Retrieve cached quality score for a response."""
        h = self._hash(prompt, model, temperature)
        return self._quality_scores.get(h, 0.0)

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(1, total) * 100, 1),
        }


_cache: Optional[AIResponseCache] = None

def get_ai_cache() -> AIResponseCache:
    global _cache
    if _cache is None:
        _cache = AIResponseCache()
    return _cache


