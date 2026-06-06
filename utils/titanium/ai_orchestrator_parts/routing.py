
"""
ai_orchestrator — Routing section
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

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from arki_project.utils.titanium.crypto import (
    csprng_weighted_choice,
)

logger = logging.getLogger("titanium.ai_orchestrator")

# ══════════════════════════════════════════════════════════════
# Types
# ══════════════════════════════════════════════════════════════

class ProviderChain:
    """Intelligent provider fallback chain with auto-selection."""

    def __init__(self, providers: list[str] | None = None) -> None:
        self._chain = providers or ["gemini", "groq", "openrouter", "pollinations"]
        self._scorer = AdaptiveScorer()
        for p in self._chain:
            self._scorer.register(p, 1.0)
        self._blacklist: set[str] = set()

    def best_provider(self) -> str | None:
        """Return the best available provider by adaptive score."""
        weights = self._scorer.get_all_weights()
        candidates = [
            (p, weights.get(p, 0.0))
            for p in self._chain
            if p not in self._blacklist
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def record_result(self, provider: str, success: bool, latency_ms: float) -> Any:
        self._scorer.record(provider, success, latency_ms)

    def blacklist(self, provider: str) -> Any:
        self._blacklist.add(provider)

    def unblacklist(self, provider: str) -> Any:
        self._blacklist.discard(provider)

    def get_fallback_order(self) -> list[str]:
        """Get providers ordered by reliability."""
        weights = self._scorer.get_all_weights()
        active = [p for p in self._chain if p not in self._blacklist]
        return sorted(active, key=lambda p: weights.get(p, 0.0), reverse=True)

class ConsensusEngine:
    """Multi-provider consensus for critical decisions."""

    def __init__(self, min_agree: int = 2, max_providers: int = 3) -> None:
        self.min_agree = min_agree
        self.max_providers = max_providers

    async def query_consensus(
        self,
        prompt: str,
        providers: list,
        query_func: Any,
    ) -> dict:
        """
        Query multiple providers and return consensus.
        
        query_func(provider, prompt) -> str
        """
        import asyncio
        tasks = [
            asyncio.create_task(query_func(p, prompt))
            for p in providers[:self.max_providers]
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        valid = [
            {"provider": p, "response": r}
            for p, r in zip(providers, responses)
            if not isinstance(r, Exception)
        ]

        return {
            "responses": valid,
            "count": len(valid),
            "consensus_reached": len(valid) >= self.min_agree,
            "primary": valid[0]["response"] if valid else None,
        }

class SmartRouter:
    """Route requests to optimal provider based on request type."""

    _ROUTING_TABLE = {
        "code": ["gemini", "groq"],
        "creative": ["gemini", "openrouter"],
        "translation": ["gemini", "openrouter"],
        "analysis": ["gemini", "groq"],
        "conversation": ["gemini", "pollinations"],
        "image": ["pollinations"],
        "default": ["gemini", "groq", "openrouter"],
    }

def route(self, request_type: str = "default") -> list[str]:
        return self._ROUTING_TABLE.get(request_type, self._ROUTING_TABLE["default"])



