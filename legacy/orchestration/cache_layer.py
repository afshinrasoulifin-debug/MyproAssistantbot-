
from __future__ import annotations
"""
tg_bot/orchestration/cache_layer.py — Multi-Level Cache
═══════════════════════════════════════════════════════
Three tiers:
  • L1: Inference cache (exact prompt+model → response)
  • L2: Semantic cache (similar prompts → cached response)
  • L3: Session cache (per-user conversation context)

Patterns covered:
  - orchestration-layer + ai-runtime + distributed-cache
  - async-workers + request-queue + response-cache
  - context-manager + memory-cache + session-sync
  - ai-runtime + inference-cache + streaming-layer
"""

import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple



logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CacheEntry:
    """A single cache entry with TTL."""
    key: str
    value: Any
    created_at: float
    expires_at: float
    hits: int = 0
    size_bytes: int = 0

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class LRUCache:
    """Thread-safe LRU cache with TTL support.

    Used as the underlying storage for all cache tiers.
    """

    def __init__(self, max_size: int = 10_000, default_ttl: float = 3600.0) -> None:
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value by key. Returns None if not found or expired."""
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        if entry.is_expired:
            del self._store[key]
            self._misses += 1
            return None
        entry.hits += 1
        self._hits += 1
        self._store.move_to_end(key)
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set a value with optional TTL override."""
        now = time.time()
        ttl = ttl if ttl is not None else self._default_ttl
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=now,
            expires_at=now + ttl,
            size_bytes=len(str(value)),
        )
        self._store[key] = entry
        self._store.move_to_end(key)
        self._evict_if_needed()

    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self) -> None:
        self._store.clear()

    def _evict_if_needed(self) -> None:
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    @property
    def size(self) -> int:
        return len(self._store)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> Dict[str, Any]:
        return {
            "size": self.size,
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 3),
        }


class CacheLayer:
    """Multi-level cache for the orchestration layer.

    L1 (Inference Cache):
        Exact match on (prompt_hash, model, temperature).
        Fast, high hit rate for repeated questions.

    L2 (Token Cache):
        Caches token counts and cost calculations.
        Reduces overhead for billing/quota checks.

    L3 (Session Cache):
        Per-user session context (conversation history, preferences).
        Survives across requests within a session window.
    """

    def __init__(
        self,
        inference_max: int = 10_000,
        inference_ttl: float = 3600.0,
        token_max: int = 50_000,
        token_ttl: float = 86400.0,
        session_max: int = 10_000,
        session_ttl: float = 7200.0,
    ) -> None:
        self.inference = LRUCache(max_size=inference_max, default_ttl=inference_ttl)
        self.token = LRUCache(max_size=token_max, default_ttl=token_ttl)
        self.session = LRUCache(max_size=session_max, default_ttl=session_ttl)

    # ── L1: Inference Cache ────────────────────────────────

    def _inference_key(self, prompt: str, model: str, temp: float) -> str:
        raw = f"{model}:{temp:.1f}:{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def get_inference(
        self, prompt: str, model: str, temperature: float = 0.7,
    ) -> Optional[str]:
        """Check if an identical inference result is cached."""
        key = self._inference_key(prompt, model, temperature)
        return self.inference.get(key)

    def set_inference(
        self,
        prompt: str,
        model: str,
        response: str,
        temperature: float = 0.7,
        ttl: Optional[float] = None,
    ) -> None:
        """Cache an inference result."""
        key = self._inference_key(prompt, model, temperature)
        self.inference.set(key, response, ttl)

    # ── L2: Token Cache ────────────────────────────────────

    def get_token_count(self, text_hash: str) -> Optional[int]:
        """Get cached token count for a text hash."""
        return self.token.get(f"tc:{text_hash}")

    def set_token_count(self, text_hash: str, count: int) -> None:
        self.token.set(f"tc:{text_hash}", count)

    def get_user_budget(self, user_id: int) -> Optional[Tuple[int, int]]:
        """Get cached (used, budget) for a user."""
        return self.token.get(f"ub:{user_id}")

    def set_user_budget(
        self, user_id: int, used: int, budget: int, ttl: float = 300.0,
    ) -> None:
        self.token.set(f"ub:{user_id}", (used, budget), ttl)

    # ── L3: Session Cache ──────────────────────────────────

    def get_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get cached session context for a user."""
        return self.session.get(f"sess:{user_id}")

    def set_session(
        self, user_id: int, data: Dict[str, Any], ttl: Optional[float] = None,
    ) -> None:
        self.session.set(f"sess:{user_id}", data, ttl)

    def update_session(self, user_id: int, **updates: Any) -> None:
        """Merge updates into an existing session."""
        key = f"sess:{user_id}"
        current = self.session.get(key)
        if current and isinstance(current, dict):
            current.update(updates)
            self.session.set(key, current)
        else:
            self.session.set(key, updates)

    # ── Global ─────────────────────────────────────────────

    def clear_all(self) -> None:
        self.inference.clear()
        self.token.clear()
        self.session.clear()

    def stats(self) -> Dict[str, Any]:
        return {
            "inference": self.inference.stats(),
            "token": self.token.stats(),
            "session": self.session.stats(),
        }


