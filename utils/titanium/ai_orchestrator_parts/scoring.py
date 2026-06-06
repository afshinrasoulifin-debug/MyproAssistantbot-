
"""
ai_orchestrator — Scoring section
"""

from __future__ import annotations
"""
tg_bot/utils/titanium/ai_orchestrator.py — TITANIUM Multi-Tier AI Orchestrator v10.3.1
══════════════════════════════════════════════════════════════════════════════════════
Features:
  • Race mode (parallel providers, first success wins, losers cancelled)
  • Weighted CSPRNG selection (cryptographically secure, not Math.random)
  • Consensus mode (NEW: call N providers, pick best/majority answer)
  • Adaptive scoring (NEW: auto-adjust weights from success/latency history)
  • Response caching (NEW: LRU cache with TTL for identical prompts)
  • 4-level fallback chain (ultra → pro → lite → free) with 0-delay failover
  • All calls through ShieldedClient (L1-L7 security)
  • No timeout limits — 300s max per provider
  • No rate limits on orchestrator itself
  • Auto-retry at provider level (3 attempts)
  • Per-provider health tracking feeds adaptive weights
  • Anthropic + OpenAI + additional provider support
  • Persian + English command aliases

Tiers:
  ULTRA — Race mode: parallel call to all providers, fastest wins
  PRO   — Adaptive weighted: intelligent selection with auto-adjusting weights
  LITE  — Single cheapest/fastest provider
  FREE  — Pollinations or similar free API (always available)

Ported from: TITANIUM ZKI core/ai_orchestrator.ts
"""

import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from arki_project.utils.titanium.config import TITANIUM_CONFIG
from arki_project.utils.titanium.crypto import (
    csprng_weighted_choice,
)

logger = logging.getLogger("titanium.ai_orchestrator")

# ══════════════════════════════════════════════════════════════
# Types
# ══════════════════════════════════════════════════════════════

class AdaptiveScorer:
    """
    Tracks provider success/latency and auto-adjusts weights.

    Scoring formula:
      score = success_rate * (1 / normalized_latency) * base_weight
      Decayed over time with exponential moving average.
    """

    EMA_ALPHA = TITANIUM_CONFIG.get('ai_adaptive_ema_alpha', 0.3)
    MIN_WEIGHT = 0.1

    def __init__(self) -> None:
        self._success_ema: Dict[str, float] = {}       # EMA of success rate
        self._latency_ema: Dict[str, float] = {}        # EMA of latency in ms
        self._call_counts: Dict[str, int] = {}
        self._base_weights: Dict[str, float] = {}

    def register(self, provider_id: str, base_weight: float) -> None:
        """Register a provider with its base weight."""
        self._base_weights[provider_id] = base_weight
        self._success_ema.setdefault(provider_id, 1.0)
        self._latency_ema.setdefault(provider_id, 1000.0)
        self._call_counts.setdefault(provider_id, 0)

    def record(self, provider_id: str, success: bool, latency_ms: float) -> None:
        """Record a call result for adaptive scoring."""
        d = self.EMA_ALPHA
        self._call_counts[provider_id] = self._call_counts.get(provider_id, 0) + 1

        old_success = self._success_ema.get(provider_id, 1.0)
        self._success_ema[provider_id] = d * old_success + (1 - d) * (1.0 if success else 0.0)

        if success and latency_ms > 0:
            old_latency = self._latency_ema.get(provider_id, 1000.0)
            self._latency_ema[provider_id] = d * old_latency + (1 - d) * latency_ms

    def get_weight(self, provider_id: str) -> float:
        """Get the current adaptive weight for a provider."""
        base = self._base_weights.get(provider_id, 1.0)
        success_rate = self._success_ema.get(provider_id, 1.0)
        avg_latency = self._latency_ema.get(provider_id, 1000.0)

        # Faster + more reliable = higher score
        speed_factor = 1000.0 / max(avg_latency, 100)  # normalize to 1.0 = 1s
        score = base * success_rate * speed_factor

        return max(self.MIN_WEIGHT, score)

    def get_all_weights(self) -> Dict[str, float]:
        """Get all current adaptive weights."""
        return {pid: self.get_weight(pid) for pid in self._base_weights}

    @property
    def stats(self) -> dict:
        return {
            pid: {
                "weight": round(self.get_weight(pid), 3),
                "success_ema": round(self._success_ema.get(pid, 0), 3),
                "latency_ema": round(self._latency_ema.get(pid, 0), 1),
                "calls": self._call_counts.get(pid, 0),
            }
            for pid in self._base_weights
        }

class ResponseCache:
    """
    LRU response cache with TTL.

    Caches identical prompt → response mappings to avoid
    duplicate API calls within a short window.
    """

    def __init__(self, max_size: int = 500, ttl_seconds: float = 300) -> None:
        self._cache: OrderedDict[str, Tuple[str, float, str]] = OrderedDict()  # key → (text, expiry, model)
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0

    def _key(self, messages: List[Dict], temperature: float) -> str:
        raw = json.dumps(messages, sort_keys=True) + f":{temperature}"
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def get(self, messages: List[Dict], temperature: float) -> Optional[Tuple[str, str]]:
        """Get cached response. Returns (text, model) or None."""
        k = self._key(messages, temperature)
        if k in self._cache:
            text, expiry, model = self._cache[k]
            if time.monotonic() < expiry:
                self._hits += 1
                self._cache.move_to_end(k)
                return text, model
            else:
                del self._cache[k]
        self._misses += 1
        return None

    def set(self, messages: List[Dict], temperature: float, text: str, model: str) -> None:
        """Cache a response."""
        k = self._key(messages, temperature)
        self._cache[k] = (text, time.monotonic() + self._ttl, model)
        self._cache.move_to_end(k)
        # Evict oldest if over limit
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self._hits / max(1, total):.1%}",
        }

def parse_tier_command(text: str) -> tuple[AITier | None, str]:
    """Parse tier command from user text."""
    stripped = text.strip()
    for cmd, tier in TIER_COMMANDS.items():
        if stripped.startswith(cmd):
            remaining = stripped[len(cmd):].strip()
            return tier, remaining if remaining else stripped
    return None, text



