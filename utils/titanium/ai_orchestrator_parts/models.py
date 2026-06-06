
"""
ai_orchestrator — Models section
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

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from arki_project.utils.titanium.crypto import (
    csprng_weighted_choice,
)

logger = logging.getLogger("titanium.ai_orchestrator")

# ══════════════════════════════════════════════════════════════
# Types
# ══════════════════════════════════════════════════════════════

class AITier(str, Enum):
    ULTRA = "ultra"
    PRO = "pro"
    LITE = "lite"
    FREE = "free"

class DispatchStrategy(str, Enum):
    RACE = "race"             # Parallel, first success wins
    WEIGHTED = "weighted"     # CSPRNG adaptive weighted selection
    CONSENSUS = "consensus"   # Call N providers, pick best answer
    SINGLE = "single"         # Single provider

class AIProvider:
    """A configured AI provider endpoint."""
    id: str
    url: str
    api_key: str = ""
    model: str = ""
    weight: float = 1.0
    timeout_ms: float = 300000  # 300s (NO artificial limits)
    format: str = "openai"      # "openai" | "gemini" | "anthropic"
    # v10.4.1: Model fallback chain — if primary model fails, try next
    fallback_models: List[str] = field(default_factory=list)

class ProviderCallResult:
    """Result from calling a single provider."""
    success: bool
    text: str = ""
    provider_id: str = ""
    latency_ms: float = 0.0
    model: str = ""
    tokens_used: int = 0
    error: Optional[str] = None

class OrchestratorResult:
    """Final result from the orchestrator dispatch."""
    success: bool
    text: str = ""
    tier: AITier = AITier.PRO
    provider_id: str = ""
    strategy: DispatchStrategy = DispatchStrategy.WEIGHTED
    latency_ms: float = 0.0
    model: str = ""
    fallback_depth: int = 0
    tokens_used: int = 0
    error: Optional[str] = None

class TierConfig:
    """Configuration for a single tier."""
    providers: List[AIProvider]
    strategy: DispatchStrategy
    timeout_ms: float = 300000  # 300s



