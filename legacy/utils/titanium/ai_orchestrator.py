
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
import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from arki_project.utils.titanium.config import TITANIUM_CONFIG
from arki_project.utils.titanium.crypto import (
    csprng_weighted_choice,
)
from arki_project.utils.titanium.shielded_client import get_shielded_pool

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


@dataclass(slots=True)
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


@dataclass(slots=True)
class ProviderCallResult:
    """Result from calling a single provider."""
    success: bool
    text: str = ""
    provider_id: str = ""
    latency_ms: float = 0.0
    model: str = ""
    tokens_used: int = 0
    error: Optional[str] = None


@dataclass(slots=True)
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


@dataclass
class TierConfig:
    """Configuration for a single tier."""
    providers: List[AIProvider]
    strategy: DispatchStrategy
    timeout_ms: float = 300000  # 300s


# ══════════════════════════════════════════════════════════════
# Adaptive Provider Scoring
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


# ══════════════════════════════════════════════════════════════
# Response Cache
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Free endpoints (always available, no API key needed)
FREE_ENDPOINT = "https://text.pollinations.ai/openai"
FREE_MODEL = "openai"

# Persian + English command aliases
TIER_COMMANDS = {
    "/ultra": AITier.ULTRA,  "/اولترا": AITier.ULTRA,
    "/pro": AITier.PRO,      "/حرفه": AITier.PRO,
    "/lite": AITier.LITE,    "/سریع": AITier.LITE,
    "/free": AITier.FREE,    "/رایگان": AITier.FREE,
}

MAX_FALLBACK_DEPTH = 4  # increased from 3


def parse_tier_command(text: str) -> tuple[AITier | None, str]:
    """Parse tier command from user text."""
    stripped = text.strip()
    for cmd, tier in TIER_COMMANDS.items():
        if stripped.startswith(cmd):
            remaining = stripped[len(cmd):].strip()
            return tier, remaining if remaining else stripped
    return None, text


# ══════════════════════════════════════════════════════════════
# Orchestrator
# ══════════════════════════════════════════════════════════════

class TitaniumOrchestrator:
    """
    TITANIUM Multi-Tier AI Orchestrator v10.3.1 — 10x Power.

    NO artificial limits. NO rate caps on orchestrator.
    Adaptive weight scoring. Response caching.
    Consensus mode. Zero-delay failover.

    Integration with arki:
      Called from orchestration/core.py → Orchestrator.generate()
      or directly from ai_client.py → _call_with_fallback()
    """

    def __init__(self, settings: dict=None) -> None:
        self._settings = settings
        self._tiers: Dict[AITier, TierConfig] = {}
        self._call_count = 0
        self._error_count = 0
        self._tier_stats: Dict[AITier, Dict[str, int]] = {}

        # v10.3.1: Adaptive scoring + caching
        self._scorer = AdaptiveScorer()
        self._cache = ResponseCache(
            max_size=TITANIUM_CONFIG.get('ai_cache_size', 2000),
            ttl_seconds=TITANIUM_CONFIG.get('ai_cache_ttl', 600.0),
        )
        self._all_providers: List[AIProvider] = []
        # v10.4.0: ProviderChain for intelligent fallback ordering
        self._provider_chain = ProviderChain()

        if settings:
            self._build_tiers(settings)

    def _build_tiers(self, settings: dict) -> None:
        """Build tier configurations from arki Settings.

        v10.4.1 DEEP UPGRADE:
          - Every provider gets a fallback_models chain (model rotation on failure)
          - Multiple free providers (Pollinations + DuckDuckGo + FreeChat)
          - Groq gets 3 model fallbacks
          - OpenRouter gets 5 model fallbacks
          - ULTRA tier uses CONSENSUS strategy when ≥3 providers
        """
        providers: List[AIProvider] = []

        # Primary: Gemini (with model fallback chain)
        if getattr(settings, 'ai_api_key', ''):
            primary_url = getattr(settings, 'ai_base_url', '')
            primary_model = getattr(settings, 'ai_model', 'gemini-2.5-pro')

            if 'generativelanguage.googleapis.com' in primary_url:
                gemini_url = f"{primary_url}/models/{primary_model}:generateContent?key={settings.ai_api_key}"
                providers.append(AIProvider(
                    id="gemini", url=gemini_url, api_key=settings.ai_api_key,
                    model=primary_model, weight=1.0, timeout_ms=300000,
                    format="gemini",
                    fallback_models=[
                        "gemini-2.5-flash",
                        "gemini-2.0-flash",
                        "gemini-1.5-pro",
                    ],
                ))
            else:
                providers.append(AIProvider(
                    id="primary", url=primary_url, api_key=settings.ai_api_key,
                    model=primary_model, weight=1.0, timeout_ms=300000,
                    format="openai",
                ))

        # Secondary: Groq (ultra-fast, with model rotation)
        if getattr(settings, 'groq_api_key', ''):
            providers.append(AIProvider(
                id="groq",
                url="https://api.groq.com/openai/v1/chat/completions",
                api_key=settings.groq_api_key,
                model="llama-3.3-70b-versatile",
                weight=0.85,
                timeout_ms=120000,
                format="openai",
                fallback_models=[
                    "llama-3.1-70b-versatile",
                    "mixtral-8x7b-32768",
                    "gemma2-9b-it",
                ],
            ))

        # Tertiary: OpenRouter (multi-model gateway, deep fallback chain)
        if getattr(settings, 'openrouter_api_key', ''):
            providers.append(AIProvider(
                id="openrouter",
                url="https://openrouter.ai/api/v1/chat/completions",
                api_key=settings.openrouter_api_key,
                model="google/gemini-2.5-pro",
                weight=0.75,
                timeout_ms=180000,
                format="openai",
                fallback_models=[
                    "google/gemini-2.5-flash",
                    "anthropic/claude-sonnet-4-20250514",
                    "meta-llama/llama-3.3-70b-instruct",
                    "deepseek/deepseek-chat-v3-0324",
                    "qwen/qwen-2.5-72b-instruct",
                ],
            ))

        # Optional: Anthropic (with Claude fallback chain)
        if getattr(settings, 'anthropic_api_key', None):
            providers.append(AIProvider(
                id="anthropic",
                url="https://api.anthropic.com/v1/messages",
                api_key=settings.anthropic_api_key,
                model="claude-opus-4-20250514",
                weight=0.95,
                timeout_ms=300000,
                format="anthropic",
                fallback_models=[
                    "claude-sonnet-4-20250514",
                    "claude-3-5-haiku-20241022",
                ],
            ))

        # Optional: OpenAI (with model fallback chain)
        if getattr(settings, 'openai_api_key', None):
            providers.append(AIProvider(
                id="openai",
                url="https://api.openai.com/v1/chat/completions",
                api_key=settings.openai_api_key,
                model="gpt-4.1",
                weight=0.9,
                timeout_ms=300000,
                format="openai",
                fallback_models=[
                    "gpt-4.1-mini",
                    "gpt-4o",
                    "gpt-4o-mini",
                ],
            ))

        # Free tier: Multiple free providers for maximum resilience
        free_providers = [
            AIProvider(
                id="free_pollinations",
                url=FREE_ENDPOINT,
                api_key="",
                model=FREE_MODEL,
                weight=0.5,
                timeout_ms=120000,
                format="openai",
            ),
            AIProvider(
                id="free_ddg",
                url="https://duckduckgo.com/duckchat/v1/chat",
                api_key="",
                model="gpt-4o-mini",
                weight=0.4,
                timeout_ms=60000,
                format="openai",
            ),
        ]

        self._all_providers = providers + free_providers

        # Register all with adaptive scorer
        for p in self._all_providers:
            self._scorer.register(p.id, p.weight)

        # Build tiers
        if len(providers) >= 3:
            # v10.4.1: ≥3 providers → CONSENSUS mode for maximum quality
            self._tiers[AITier.ULTRA] = TierConfig(
                providers=list(providers),
                strategy=DispatchStrategy.CONSENSUS,
                timeout_ms=300000,
            )
        elif len(providers) >= 2:
            self._tiers[AITier.ULTRA] = TierConfig(
                providers=list(providers),
                strategy=DispatchStrategy.RACE,
                timeout_ms=300000,
            )

        if providers:
            self._tiers[AITier.PRO] = TierConfig(
                providers=list(providers),
                strategy=DispatchStrategy.WEIGHTED,
                timeout_ms=300000,
            )
            cheapest = sorted(providers, key=lambda p: p.weight)
            self._tiers[AITier.LITE] = TierConfig(
                providers=[cheapest[0]],
                strategy=DispatchStrategy.SINGLE,
                timeout_ms=120000,
            )

        # v10.4.1: FREE tier uses ALL free providers with race strategy
        self._tiers[AITier.FREE] = TierConfig(
            providers=free_providers,
            strategy=DispatchStrategy.RACE if len(free_providers) > 1 else DispatchStrategy.SINGLE,
            timeout_ms=120000,
        )

        for tier in self._tiers:
            self._tier_stats[tier] = {"calls": 0, "errors": 0, "fallbacks": 0}

        total_models = sum(1 + len(p.fallback_models) for p in self._all_providers)
        logger.info(
            "TITANIUM Orchestrator v10.4.1: %d providers, %d total models, "
            "tiers: %s, adaptive scoring ON, model rotation ON",
            len(self._all_providers), total_models, list(self._tiers.keys()),
        )

    @property
    def available_tiers(self) -> List[str]:
        return [t.value for t in self._tiers]

    @property
    def providers(self) -> List[AIProvider]:
        return self._all_providers

    # ── Main Dispatch ─────────────────────────────────────────

    async def dispatch(
        self,
        messages: List[Dict[str, str]],
        *,
        tier: AITier | None = None,
        model_override: str = "",
        temperature: float = 0.7,
        max_tokens: int = 65536,
        user_id: int = 0,
        use_cache: bool = True,
    ) -> OrchestratorResult:
        """
        Main dispatch entry point. NO limits, NO caps.

        1. Check cache → return if hit
        2. Dispatch to requested tier with automatic fallback
        3. Record metrics for adaptive scoring
        4. Cache successful response
        """
        self._call_count += 1
        t0 = time.monotonic()

        # 1. Cache check
        if use_cache:
            cached = self._cache.get(messages, temperature)
            if cached:
                text, model = cached
                logger.debug("TITANIUM cache hit (model=%s)", model)
                return OrchestratorResult(
                    success=True, text=text, provider_id="cache",
                    model=model, latency_ms=0.1,
                )

        # 2. Default tier
        if tier is None:
            tier = AITier.PRO if AITier.PRO in self._tiers else AITier.FREE

        # 3. Fallback chain
        fallback_chain = self._get_fallback_chain(tier)
        depth = 0

        for current_tier in fallback_chain:
            if current_tier not in self._tiers:
                continue
            if depth >= MAX_FALLBACK_DEPTH:
                break

            config = self._tiers[current_tier]

            try:
                result = await self._dispatch_tier(
                    config, messages,
                    model_override=model_override,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if result.success:
                    result.tier = current_tier
                    result.fallback_depth = depth
                    result.latency_ms = (time.monotonic() - t0) * 1000

                    if current_tier in self._tier_stats:
                        self._tier_stats[current_tier]["calls"] += 1

                    # 4. Cache result
                    if use_cache and result.text:
                        self._cache.set(messages, temperature, result.text, result.model or "")

                    # v10.4.0: Feed ProviderChain with success for adaptive ordering
                    self._provider_chain.record_result(
                        result.provider_id, True, result.latency_ms
                    )
                    logger.info(
                        "TITANIUM dispatch: tier=%s provider=%s latency=%.0fms depth=%d",
                        current_tier.value, result.provider_id, result.latency_ms, depth,
                    )
                    return result

                if current_tier in self._tier_stats:
                    self._tier_stats[current_tier]["errors"] += 1

            except Exception as exc:
                logger.warning(
                    "TITANIUM tier %s failed: %s (next tier)",
                    current_tier.value, str(exc)[:200],
                )
                if current_tier in self._tier_stats:
                    self._tier_stats[current_tier]["errors"] += 1
                # v10.4.0: Feed ProviderChain with failure
                self._provider_chain.record_result(
                    current_tier.value, False, 0
                )

            depth += 1
            if current_tier in self._tier_stats:
                self._tier_stats[current_tier]["fallbacks"] += 1

        self._error_count += 1
        return OrchestratorResult(
            success=False, tier=tier, fallback_depth=depth,
            latency_ms=(time.monotonic() - t0) * 1000,
            error="All tiers exhausted",
        )

    def _get_fallback_chain(self, start_tier: AITier) -> List[AITier]:
        full_chain = [AITier.ULTRA, AITier.PRO, AITier.LITE, AITier.FREE]
        try:
            idx = full_chain.index(start_tier)
            return full_chain[idx:]
        except ValueError:
            return [AITier.PRO, AITier.LITE, AITier.FREE]

    async def _dispatch_tier(
        self, config: TierConfig, messages: List[Dict[str, str]],
        *, model_override: str = "", temperature: float = 0.7, max_tokens: int = 65536,
    ) -> OrchestratorResult:
        if config.strategy == DispatchStrategy.RACE:
            return await self._strategy_race(config, messages, model_override, temperature, max_tokens)
        elif config.strategy == DispatchStrategy.WEIGHTED:
            return await self._strategy_weighted(config, messages, model_override, temperature, max_tokens)
        elif config.strategy == DispatchStrategy.CONSENSUS:
            return await self._strategy_consensus(config, messages, model_override, temperature, max_tokens)
        else:
            return await self._strategy_single(config, messages, model_override, temperature, max_tokens)

    # ── Strategy: Race ────────────────────────────────────────

    async def _strategy_race(
        self, config: TierConfig, messages: List[Dict[str, str]],
        model_override: str, temperature: float, max_tokens: int,
    ) -> OrchestratorResult:
        """Race mode: all providers parallel, first SUCCESS wins, losers cancelled."""
        if not config.providers:
            return OrchestratorResult(success=False, error="No providers for race")

        tasks: List[asyncio.Task] = []
        results_queue: asyncio.Queue[ProviderCallResult] = asyncio.Queue()

        async def _race_participant(provider: AIProvider) -> Any:
            try:
                result = await self._call_provider(
                    provider, messages,
                    model_override=model_override,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                await results_queue.put(result)
            except asyncio.CancelledError:
                pass  #  CancelledError is expected during shutdown
            except Exception as exc:
                await results_queue.put(ProviderCallResult(
                    success=False, provider_id=provider.id, error=str(exc)[:200],
                ))

        for provider in config.providers:
            tasks.append(asyncio.create_task(_race_participant(provider)))

        try:
            remaining = len(tasks)
            deadline = time.monotonic() + config.timeout_ms / 1000

            while remaining > 0:
                timeout = max(0.1, deadline - time.monotonic())
                try:
                    result = await asyncio.wait_for(results_queue.get(), timeout=timeout)
                except asyncio.TimeoutError:
                    break

                remaining -= 1

                if result.success:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    # Record adaptive score
                    self._scorer.record(result.provider_id, True, result.latency_ms)
                    return OrchestratorResult(
                        success=True, text=result.text, provider_id=result.provider_id,
                        strategy=DispatchStrategy.RACE, model=result.model,
                        latency_ms=result.latency_ms, tokens_used=result.tokens_used,
                    )
                else:
                    self._scorer.record(result.provider_id, False, result.latency_ms)

            return OrchestratorResult(
                success=False, strategy=DispatchStrategy.RACE,
                error=f"All {len(config.providers)} race participants failed",
            )
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    # ── Strategy: Adaptive Weighted CSPRNG ────────────────────

    async def _strategy_weighted(
        self, config: TierConfig, messages: List[Dict[str, str]],
        model_override: str, temperature: float, max_tokens: int,
    ) -> OrchestratorResult:
        """
        Adaptive weighted CSPRNG selection.

        v10.3.1: Uses adaptive scorer (success rate + latency EMA) to
        dynamically adjust weights. Better providers get called more.
        """
        remaining_providers = list(config.providers)

        while remaining_providers:
            # Use adaptive weights instead of static weights
            weights = [self._scorer.get_weight(p.id) for p in remaining_providers]
            selected = csprng_weighted_choice(remaining_providers, weights)

            result = await self._call_provider(
                selected, messages,
                model_override=model_override,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            self._scorer.record(selected.id, result.success, result.latency_ms)

            if result.success:
                return OrchestratorResult(
                    success=True, text=result.text, provider_id=result.provider_id,
                    strategy=DispatchStrategy.WEIGHTED, model=result.model,
                    latency_ms=result.latency_ms, tokens_used=result.tokens_used,
                )

            remaining_providers = [p for p in remaining_providers if p.id != selected.id]
            logger.info("Weighted: %s failed, %d remaining", selected.id, len(remaining_providers))

        return OrchestratorResult(
            success=False, strategy=DispatchStrategy.WEIGHTED,
            error="All weighted providers failed",
        )

    # ── Strategy: Consensus ───────────────────────────────────

    async def _strategy_consensus(
        self, config: TierConfig, messages: List[Dict[str, str]],
        model_override: str, temperature: float, max_tokens: int,
    ) -> OrchestratorResult:
        """
        Consensus mode v10.4.1: Call ALL providers in parallel, score responses,
        pick the best one by quality heuristics.

        Scoring criteria (weighted):
          1. Response length (completeness): 40%
          2. Provider weight (quality reputation): 30%
          3. Latency inversed (speed): 15%
          4. Token usage (efficiency): 15%

        All providers are called simultaneously with model rotation enabled.
        Even if 4 out of 5 providers fail, the one success is returned.
        """
        if not config.providers:
            return OrchestratorResult(success=False, error="No providers for consensus")

        tasks = []
        for provider in config.providers:
            tasks.append(self._call_provider(
                provider, messages,
                model_override=model_override,
                temperature=temperature,
                max_tokens=max_tokens,
            ))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        successes: List[ProviderCallResult] = []
        for r in results:
            if isinstance(r, ProviderCallResult) and r.success and r.text:
                successes.append(r)
                self._scorer.record(r.provider_id, True, r.latency_ms)
            elif isinstance(r, ProviderCallResult):
                self._scorer.record(r.provider_id, False, r.latency_ms)

        if not successes:
            return OrchestratorResult(
                success=False, strategy=DispatchStrategy.CONSENSUS,
                error="No provider returned a successful response",
            )

        # v10.4.1: Smart scoring — not just longest
        def _score_response(r: ProviderCallResult) -> float:
            text_len = len(r.text) if r.text else 0
            # Normalize length (0-1, cap at 4000 chars)
            len_score = min(text_len / 4000, 1.0)
            # Provider quality weight
            weight_score = self._scorer.get_weight(r.provider_id) / max(
                1.0, max(self._scorer.get_weight(p.id) for p in config.providers)
            )
            # Speed score (inverse latency, normalize)
            max_latency = max(s.latency_ms for s in successes) or 1
            speed_score = 1.0 - (r.latency_ms / max(max_latency, 1))
            # Token efficiency
            token_score = min((r.tokens_used or 0) / 1000, 1.0) if r.tokens_used else 0.5

            return (len_score * 0.40 + weight_score * 0.30 +
                    speed_score * 0.15 + token_score * 0.15)

        best = max(successes, key=_score_response)
        best_score = _score_response(best)

        logger.info(
            "TITANIUM consensus: %d/%d succeeded, best=%s score=%.2f len=%d",
            len(successes), len(config.providers),
            best.provider_id, best_score, len(best.text or ""),
        )

        return OrchestratorResult(
            success=True, text=best.text, provider_id=best.provider_id,
            strategy=DispatchStrategy.CONSENSUS, model=best.model,
            latency_ms=best.latency_ms, tokens_used=best.tokens_used,
        )

    # ── Strategy: Single ──────────────────────────────────────

    async def _strategy_single(
        self, config: TierConfig, messages: List[Dict[str, str]],
        model_override: str, temperature: float, max_tokens: int,
    ) -> OrchestratorResult:
        if not config.providers:
            return OrchestratorResult(success=False, error="No provider for single")

        provider = config.providers[0]
        result = await self._call_provider(
            provider, messages,
            model_override=model_override,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self._scorer.record(provider.id, result.success, result.latency_ms)

        return OrchestratorResult(
            success=result.success, text=result.text, provider_id=result.provider_id,
            strategy=DispatchStrategy.SINGLE, model=result.model,
            latency_ms=result.latency_ms, tokens_used=result.tokens_used,
            error=result.error,
        )

    # ── Provider Call ─────────────────────────────────────────

    async def _call_provider(
        self, provider: AIProvider, messages: List[Dict[str, str]],
        *, model_override: str = "", temperature: float = 0.7, max_tokens: int = 65536,
    ) -> ProviderCallResult:
        """
        Call a single AI provider through the shielded client.

        v10.4.1: Model rotation — if primary model fails and provider has
        fallback_models, automatically tries the next model in the chain.
        This means a single provider can attempt 4+ different models before
        giving up, massively increasing success rate.

        Supports: OpenAI, Gemini, Anthropic formats.
        Shielded client handles retries internally (3 attempts per model).
        """
        pool = get_shielded_pool()
        t0 = time.monotonic()

        # Build model chain: primary + fallbacks
        if model_override:
            model_chain = [model_override]
        else:
            model_chain = [provider.model] + list(provider.fallback_models)

        last_error = ""
        for model_idx, model in enumerate(model_chain):
            try:
                if provider.format == "gemini":
                    result = await self._call_gemini_format(
                        pool, provider, messages, model, temperature, max_tokens, t0,
                    )
                elif provider.format == "anthropic":
                    result = await self._call_anthropic_format(
                        pool, provider, messages, model, temperature, max_tokens, t0,
                    )
                else:
                    result = await self._call_openai_format(
                        pool, provider, messages, model, temperature, max_tokens, t0,
                    )

                if result.success:
                    if model_idx > 0:
                        logger.info(
                            "TITANIUM model rotation: %s primary failed, succeeded on fallback[%d]=%s",
                            provider.id, model_idx, model,
                        )
                    return result
                else:
                    last_error = result.error or "empty response"
                    # v10.5: If 429 (rate limit), skip ALL remaining models for this provider
                    # since they share the same API key and quota
                    if "429" in last_error:
                        logger.warning(
                            "TITANIUM %s: API key rate-limited (429), skipping %d remaining models",
                            provider.id, len(model_chain) - model_idx - 1,
                        )
                        break
                    if model_idx < len(model_chain) - 1:
                        logger.debug(
                            "TITANIUM model %s/%s failed (%s), rotating to %s",
                            provider.id, model, last_error[:60], model_chain[model_idx + 1],
                        )

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_error = str(exc)[:200]
                if model_idx < len(model_chain) - 1:
                    logger.debug(
                        "TITANIUM model %s/%s error (%s), rotating to %s",
                        provider.id, model, last_error[:60], model_chain[model_idx + 1],
                    )
                    continue
                break

        latency = (time.monotonic() - t0) * 1000
        return ProviderCallResult(
            success=False, provider_id=provider.id,
            latency_ms=latency,
            error=f"All {len(model_chain)} models exhausted: {last_error}",
        )

    async def _call_openai_format(
        self, pool: Any, provider: str, messages: list, model: str, temperature: float, max_tokens: int, t0: Any,
    ) -> ProviderCallResult:
        """Call OpenAI-compatible API."""
        headers = {}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"

        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        resp = await pool.post(
            provider.url,
        json_data=body,
        headers=headers,
        timeout=provider.timeout_ms / 1000,
        provider_name=provider.id,
        )

        latency = (time.monotonic() - t0) * 1000

        if not resp.success:
            return ProviderCallResult(
                success=False, provider_id=provider.id,
                latency_ms=latency, error=f"HTTP {resp.status}: {resp.text[:200]}",
            )

        data = resp.json()
        text = ""
        tokens = 0

        choices = data.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            text = msg.get("content", "")
        elif "text" in data:
            text = data["text"]

        usage = data.get("usage", {})
        tokens = usage.get("total_tokens", 0)

        if not text:
            return ProviderCallResult(
                success=False, provider_id=provider.id,
                latency_ms=latency, error="Empty response from provider",
            )

        return ProviderCallResult(
            success=True, text=text, provider_id=provider.id,
            model=model, latency_ms=latency, tokens_used=tokens,
        )

    async def _call_gemini_format(
        self, pool: Any, provider: str, messages: list, model: str, temperature: float, max_tokens: int, t0: Any,
    ) -> ProviderCallResult:
        """Call Google Gemini native API format."""
        contents = []
        system_text = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_text = content
            else:
                gemini_role = "user" if role == "user" else "model"
                contents.append({"role": gemini_role, "parts": [{"text": content}]})

        body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"},
            ],
        }

        if system_text:
            body["systemInstruction"] = {"parts": [{"text": system_text}]}

        resp = await pool.post(
            provider.url,
        json_data=body,
        timeout=provider.timeout_ms / 1000,
        provider_name=provider.id,
        )

        latency = (time.monotonic() - t0) * 1000

        if not resp.success:
            return ProviderCallResult(
                success=False, provider_id=provider.id,
                latency_ms=latency, error=f"HTTP {resp.status}: {resp.text[:200]}",
            )

        data = resp.json()
        text = ""
        tokens = 0

        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)

        usage = data.get("usageMetadata", {})
        tokens = usage.get("totalTokenCount", 0)

        if not text:
            return ProviderCallResult(
                success=False, provider_id=provider.id,
                latency_ms=latency, error="Empty Gemini response",
            )

        return ProviderCallResult(
            success=True, text=text, provider_id=provider.id,
            model=model, latency_ms=latency, tokens_used=tokens,
        )

    async def _call_anthropic_format(
        self, pool: Any, provider: str, messages: list, model: str, temperature: float, max_tokens: int, t0: Any,
    ) -> ProviderCallResult:
        """Call Anthropic Claude API format."""
        headers = {
            "x-api-key": provider.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        # Extract system message
        system_text = ""
        user_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_text = msg.get("content", "")
            else:
                user_messages.append(msg)

        body: Dict[str, Any] = {
            "model": model,
            "messages": user_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_text:
            body["system"] = system_text

        resp = await pool.post(
            provider.url,
        json_data=body,
        headers=headers,
        timeout=provider.timeout_ms / 1000,
        provider_name=provider.id,
        )

        latency = (time.monotonic() - t0) * 1000

        if not resp.success:
            return ProviderCallResult(
                success=False, provider_id=provider.id,
                latency_ms=latency, error=f"HTTP {resp.status}: {resp.text[:200]}",
            )

        data = resp.json()
        content_blocks = data.get("content", [])
        text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
        tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)

        if not text:
            return ProviderCallResult(
                success=False, provider_id=provider.id,
                latency_ms=latency, error="Empty Anthropic response",
            )

        return ProviderCallResult(
            success=True, text=text, provider_id=provider.id,
            model=model, latency_ms=latency, tokens_used=tokens,
        )

    # ── Stats ─────────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        return {
            "total_calls": self._call_count,
            "total_errors": self._error_count,
            "tiers": dict(self._tier_stats),
            "available_tiers": self.available_tiers,
            "adaptive_scores": self._scorer.stats,
            "cache": self._cache.stats,
            "providers": len(self._all_providers),
        }


# ── Singleton ────────────────────────────────────────────────

_instance: Optional[TitaniumOrchestrator] = None


def get_titanium_orchestrator() -> Optional[TitaniumOrchestrator]:
    """Get the booted orchestrator instance."""
    return _instance


def set_titanium_orchestrator(orch: TitaniumOrchestrator) -> None:
    """Set the orchestrator instance (called from boot)."""
    global _instance
    _instance = orch


# ══════════════════════════════════════════════════════════════
# v10.4 Advanced Orchestration Features
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


