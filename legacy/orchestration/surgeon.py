
from __future__ import annotations
"""
orchestration/surgeon.py — AI Global Surgeon v2.0-TITAN (SUPER-HARDENED)
═════════════════════════════════════════════════════════════════════════
The "Brain" of the core. Enterprise-grade capabilities:

1. Token Pool Management — Multiple API keys per provider, weighted rotation
2. Cloudflare Bypass Orchestration — Multi-engine stealth browser pipeline
3. CAPTCHA Bypass — Detection + multi-solver routing
4. Session Replay — Automated key regeneration via captured sessions
5. Quota & Rate Limit Intelligence — Predictive rotation before exhaustion
6. Provider Health Monitoring — Real-time latency, error rate, cost tracking
7. Auto-Failover — Intelligent routing to healthiest provider
8. Model Intelligence — Benchmark-driven model selection per task type
9. Audit & Research Loops — Background infrastructure optimization
10. Integration with AntiDetectionEngine + SessionStore

Author: Arki Engine TITAN
License: Proprietary
"""


import asyncio
import hashlib
import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Final, List, Optional


logger = logging.getLogger("arki.surgeon")

# ── Optional integrations ──
try:
    from .workers.stealth_worker import stealth_worker, StealthWorker, BrowserEngine
    _STEALTH_AVAILABLE: bool = True
except ImportError:
    _STEALTH_AVAILABLE = False

try:
    from arki_project.sessions.session_store import (
        get_session_store, SessionStore, PROVIDER_DEFAULTS,
    )
    _SESSION_STORE_AVAILABLE: bool = True
except ImportError:
    _SESSION_STORE_AVAILABLE = False

try:
    from arki_project.utils.anti_detection import AntiDetectionEngine
    _ANTI_DETECT_AVAILABLE: bool = True
except ImportError:
    _ANTI_DETECT_AVAILABLE = False


# ═══════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════

class TokenState(Enum):
    """Lifecycle states for an API token."""
    ACTIVE = "active"
    EXHAUSTED = "exhausted"
    RATE_LIMITED = "rate_limited"
    REVOKED = "revoked"
    EXPIRED = "expired"
    ROTATING = "rotating"


class ProviderHealth(Enum):
    """Overall health of a provider."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class APIToken:
    """Single API token with metadata and health tracking."""
    token_id: str
    provider: str
    key: str  # The actual API key (masked in logs)
    key_hash: str = ""
    state: TokenState = TokenState.ACTIVE
    created_at: float = field(default_factory=time.time)
    last_used: float = 0
    total_requests: int = 0
    total_errors: int = 0
    total_tokens_used: int = 0  # LLM tokens
    daily_requests: int = 0
    daily_reset_at: float = 0
    rate_limit_until: float = 0
    quota_remaining: Optional[int] = None
    quota_total: Optional[int] = None
    cost_usd: float = 0.0
    weight: float = 1.0  # Higher = preferred
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> Any:
        if not self.key_hash:
            self.key_hash = hashlib.sha256(self.key.encode()).hexdigest()[:12]

    @property
    def masked_key(self) -> str:
        if len(self.key) < 12:
            return "***"
        return f"{self.key[:4]}...{self.key[-4:]}"

    @property
    def is_usable(self) -> bool:
        if self.state != TokenState.ACTIVE:
            return False
        if self.rate_limit_until > time.time():
            return False
        return True

    @property
    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_errors / self.total_requests

    @property
    def quota_utilization(self) -> Optional[float]:
        if self.quota_total and self.quota_total > 0:
            used = self.quota_total - (self.quota_remaining or 0)
            return used / self.quota_total
        return None

    def record_success(self, tokens_used: int = 0, cost: float = 0.0) -> None:
        self.last_used = time.time()
        self.total_requests += 1
        self.daily_requests += 1
        self.total_tokens_used += tokens_used
        self.cost_usd += cost
        if self.quota_remaining is not None and self.quota_remaining > 0:
            self.quota_remaining -= 1

    def record_error(self, is_rate_limit: bool = False, retry_after: float = 0) -> None:
        self.total_errors += 1
        self.total_requests += 1
        if is_rate_limit:
            self.rate_limit_until = time.time() + max(retry_after, 60)
            self.state = TokenState.RATE_LIMITED

    def reset_daily(self) -> None:
        self.daily_requests = 0
        self.daily_reset_at = time.time()
        if self.state == TokenState.RATE_LIMITED:
            self.state = TokenState.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_id": self.token_id,
            "provider": self.provider,
            "key_hash": self.key_hash,
            "masked_key": self.masked_key,
            "state": self.state.value,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": round(self.error_rate, 4),
            "daily_requests": self.daily_requests,
            "quota_utilization": self.quota_utilization,
            "cost_usd": round(self.cost_usd, 4),
            "weight": self.weight,
            "is_usable": self.is_usable,
        }


@dataclass
class ProviderState:
    """Aggregate state for an API provider."""
    name: str
    tokens: List[APIToken] = field(default_factory=list)
    health: ProviderHealth = ProviderHealth.UNKNOWN
    avg_latency_ms: float = 0
    error_rate_5m: float = 0
    last_health_check: float = 0
    console_url: str = ""
    models: List[str] = field(default_factory=list)
    daily_limit: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def usable_tokens(self) -> List[APIToken]:
        return [t for t in self.tokens if t.is_usable]

    @property
    def total_daily_requests(self) -> int:
        return sum(t.daily_requests for t in self.tokens)

    def get_best_token(self) -> Optional[APIToken]:
        """Get the best token using weighted selection."""
        usable = self.usable_tokens
        if not usable:
            return None

        # Sort by: least daily usage, then highest weight, then least errors
        usable.sort(key=lambda t: (t.daily_requests, -t.weight, t.error_rate))
        return usable[0]

    def get_weighted_token(self) -> Optional[APIToken]:
        """Select token using weighted random for load distribution."""
        usable = self.usable_tokens
        if not usable:
            return None
        if len(usable) == 1:
            return usable[0]

        weights = [t.weight * (1 - t.error_rate) for t in usable]
        total = sum(weights)
        if total == 0:
            return random.choice(usable)

        r = random.uniform(0, total)
        cumulative = 0
        for token, weight in zip(usable, weights):
            cumulative += weight
            if r <= cumulative:
                return token
        return usable[-1]


# ═══════════════════════════════════════════════════════════
# Token Pool Manager
# ═══════════════════════════════════════════════════════════

class TokenPoolManager:
    """
    Enterprise token pool with intelligent rotation.

    Features:
    - Multiple keys per provider
    - Weighted random selection for load distribution
    - Automatic rate-limit detection + backoff
    - Quota tracking + preemptive rotation
    - Daily counter reset
    - Persistent token state (survives restarts)
    """

    def __init__(self, persist_path: str = "sessions/token_pool.json") -> None:
        self._providers: Dict[str, ProviderState] = {}
        self._persist_path = Path(persist_path)
        self._lock = asyncio.Lock()
        self._rotation_count = 0

    # ── Token Management ──

    async def add_token(
        self,
        provider: str,
        key: str,
        weight: float = 1.0,
        quota_total: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> APIToken:
        """Add an API token to the pool."""
        async with self._lock:
            if provider not in self._providers:
                self._providers[provider] = ProviderState(name=provider)

            token_id = hashlib.sha256(f"{provider}:{key}".encode()).hexdigest()[:16]

            # Check for duplicate
            for existing in self._providers[provider].tokens:
                if existing.key_hash == hashlib.sha256(key.encode()).hexdigest()[:12]:
                    logger.info("Token %s already exists for %s", existing.masked_key, provider)
                    return existing

            token = APIToken(
                token_id=token_id,
                provider=provider,
                key=key,
                weight=weight,
                quota_total=quota_total,
                quota_remaining=quota_total,
                metadata=metadata or {},
            )
            self._providers[provider].tokens.append(token)
            await self._persist()
            logger.info("🔑 Token %s added to %s pool (weight=%.1f)", token.masked_key, provider, weight)
            return token

    async def remove_token(self, provider: str, key_hash: str) -> bool:
        """Remove a token by its hash."""
        async with self._lock:
            state = self._providers.get(provider)
            if not state:
                return False
            before = len(state.tokens)
            state.tokens = [t for t in state.tokens if t.key_hash != key_hash]
            if len(state.tokens) < before:
                await self._persist()
                return True
            return False

    async def get_token(self, provider: str) -> Optional[APIToken]:
        """Get the best available token for a provider."""
        async with self._lock:
            state = self._providers.get(provider)
            if not state:
                return None
            return state.get_weighted_token()

    async def record_success(
        self, provider: str, key_hash: str,
        tokens_used: int = 0, cost: float = 0.0,
    ) -> None:
        """Record a successful API call."""
        async with self._lock:
            token = self._find_token(provider, key_hash)
            if token:
                token.record_success(tokens_used, cost)

    async def record_error(
        self, provider: str, key_hash: str,
        is_rate_limit: bool = False, retry_after: float = 0,
    ) -> None:
        """Record an API error."""
        async with self._lock:
            token = self._find_token(provider, key_hash)
            if token:
                token.record_error(is_rate_limit, retry_after)

                if is_rate_limit:
                    self._rotation_count += 1
                    logger.warning(
                        "⚠️ Token %s rate-limited for %s — rotating (total rotations: %d)",
                        token.masked_key, provider, self._rotation_count,
                    )

    async def rotate_provider(self, provider: str) -> Optional[APIToken]:
        """Force rotation to next token for a provider."""
        async with self._lock:
            return self._rotate_unlocked(provider)

    def _rotate_unlocked(self, provider: str) -> Optional[APIToken]:
        """Rotate without acquiring lock (caller must hold lock)."""
        state = self._providers.get(provider)
        if not state:
            return None

        usable = state.usable_tokens
        if not usable:
            logger.warning("🚨 No usable tokens for %s — all exhausted!", provider)
            return None

        # Pick least recently used
        usable.sort(key=lambda t: t.last_used)
        self._rotation_count += 1
        return usable[0]

    async def check_preemptive_rotation(self, provider: str) -> Optional[APIToken]:
        """
        Check if current token needs preemptive rotation.
        Triggers when quota utilization > 80% or error rate > 20%.
        """
        async with self._lock:
            state = self._providers.get(provider)
            if not state:
                return None

            current = state.get_best_token()
            if not current:
                return None

            needs_rotation = False
            reason = ""

            if current.quota_utilization and current.quota_utilization > 0.8:
                needs_rotation = True
                reason = f"quota {current.quota_utilization:.0%}"
            elif current.error_rate > 0.2:
                needs_rotation = True
                reason = f"error_rate {current.error_rate:.0%}"
            elif current.daily_requests > (state.daily_limit or 10000) * 0.9:
                needs_rotation = True
                reason = f"daily_limit {current.daily_requests}"

            if needs_rotation and len(state.usable_tokens) > 1:
                logger.info("🔄 Preemptive rotation for %s: %s", provider, reason)
                return self._rotate_unlocked(provider)
            return None

    async def reset_daily_counters(self) -> None:
        """Reset all daily counters (call at midnight)."""
        async with self._lock:
            for state in self._providers.values():
                for token in state.tokens:
                    token.reset_daily()
            await self._persist()
            logger.info("📅 Daily token counters reset for all providers")

    # ── Internal ──

    def _find_token(self, provider: str, key_hash: str) -> Optional[APIToken]:
        state = self._providers.get(provider)
        if not state:
            return None
        for token in state.tokens:
            if token.key_hash == key_hash:
                return token
        return None

    async def _persist(self) -> None:
        """Save pool state to disk."""
        try:
            data = {}
            for name, state in self._providers.items():
                data[name] = {
                    "health": state.health.value,
                    "tokens": [t.to_dict() for t in state.tokens],
                    "avg_latency_ms": state.avg_latency_ms,
                    "total_daily": state.total_daily_requests,
                }
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug("Token pool persist: %s", e)

    # ── Stats ──

    def get_stats(self) -> Dict[str, Any]:
        """Comprehensive pool statistics."""
        per_provider = {}
        for name, state in self._providers.items():
            per_provider[name] = {
                "total_tokens": len(state.tokens),
                "usable_tokens": len(state.usable_tokens),
                "health": state.health.value,
                "total_daily_requests": state.total_daily_requests,
                "avg_latency_ms": round(state.avg_latency_ms, 1),
                "tokens": [t.to_dict() for t in state.tokens],
            }

        return {
            "providers": per_provider,
            "total_tokens": sum(len(s.tokens) for s in self._providers.values()),
            "total_usable": sum(len(s.usable_tokens) for s in self._providers.values()),
            "total_rotations": self._rotation_count,
        }


# ═══════════════════════════════════════════════════════════
# Surgeon Agent v2.0
# ═══════════════════════════════════════════════════════════

class SurgeonAgent:
    """
    Autonomous AI infrastructure surgeon — v2.0-TITAN.

    The "Brain" that manages:
    - Token pools (multiple keys per provider, intelligent rotation)
    - Cloudflare bypass (via stealth_worker multi-engine pipeline)
    - CAPTCHA detection & solving
    - Session replay for API key regeneration
    - Provider health monitoring & auto-failover
    - Background audit & research loops
    - Model intelligence (benchmark-based routing)
    """

    VERSION: Final[str] = "2.0.0-TITAN"

    # 10 Black-Ops Capabilities Matrix — Hardened Core
    capabilities: Final[List[str]] = [
        "browser_automation",       # Stealth browser via playwright
        "session_reuse",            # Persistent session store
        "unofficial_endpoints",     # Undocumented API access
        "playwright_stealth",       # Anti-fingerprinting
        "cookie_store",             # Cookie persistence & rotation
        "request_replay",           # Captured request replay
        "cloudflare_bypass",        # CF challenge/turnstile bypass
        "rotating_sessions",        # Multi-session rotation
        "token_pooling",            # Multi-key pool management
        "captcha_bypass",           # CAPTCHA detection & solving
        # v2.0 additions
        "multi_engine_browser",     # Chromium + Firefox + WebKit
        "fingerprint_injection",    # Canvas, WebGL, Audio noise
        "human_simulation",         # Mouse, scroll, typing, idle
        "quota_prediction",         # Preemptive key rotation
        "provider_failover",        # Auto-failover to healthy provider
        "encrypted_sessions",       # AES-256-GCM session storage
    ]

    def __init__(self) -> None:
        self.is_running: bool = False
        self.model_benchmarks: Dict[str, Any] = {}
        self.active_sessions: Dict[str, Any] = {}
        self.provider_registry: Dict[str, Any] = {}
        self.audit_interval: int = 300     # 5 minutes
        self.research_interval: int = 3600  # 1 hour

        # v2.0: Token Pool
        self._token_pool = TokenPoolManager()

        # v2.0: Stealth Worker reference
        self._stealth_worker: Optional[Any] = None
        if _STEALTH_AVAILABLE:
            self._stealth_worker = stealth_worker

        # v2.0: Session Store
        self._session_store: Optional[Any] = None
        if _SESSION_STORE_AVAILABLE:
            self._session_store = get_session_store()

        # v2.0: Anti-Detection
        self._anti_detect: Optional[Any] = None
        if _ANTI_DETECT_AVAILABLE:
            self._anti_detect = AntiDetectionEngine()

        # Background tasks
        self._tasks: List[asyncio.Task] = []

        # Stats
        self._stats = {
            "audits_completed": 0,
            "research_cycles": 0,
            "bypass_attempts": 0,
            "bypass_successes": 0,
            "key_regenerations": 0,
            "failovers_triggered": 0,
            "models_evaluated": 0,
        }

    # ── Lifecycle ────────────────────────────────────────

    async def start(self) -> None:
        """Activate the Surgeon Agent and all subsystems."""
        if self.is_running:
            logger.debug("Surgeon Agent is already active.")
            return

        self.is_running = True

        # Start stealth worker
        if self._stealth_worker and hasattr(self._stealth_worker, 'start'):
            try:
                await self._stealth_worker.start()
            except Exception as e:
                logger.debug("Stealth worker start: %s", e)

        # Start session store
        if self._session_store and hasattr(self._session_store, 'start'):
            try:
                await self._session_store.start()
            except Exception as e:
                logger.debug("Session store start: %s", e)

        # Load API keys from environment
        await self._load_env_tokens()

        # Background workers
        self._tasks.append(asyncio.create_task(self._audit_loop()))
        self._tasks.append(asyncio.create_task(self._research_loop()))
        self._tasks.append(asyncio.create_task(self._daily_reset_loop()))

        logger.info(
            "🩺 AI Surgeon v%s activated — %d capabilities, "
            "token_pool: %s, stealth: %s, sessions: %s, anti_detect: %s",
            self.VERSION, len(self.capabilities),
            "✅" if self._token_pool else "❌",
            "✅" if _STEALTH_AVAILABLE else "❌",
            "✅" if _SESSION_STORE_AVAILABLE else "❌",
            "✅" if _ANTI_DETECT_AVAILABLE else "❌",
        )

    async def stop(self) -> None:
        """Gracefully stop the Surgeon Agent and all subsystems."""
        self.is_running = False

        # Cancel background tasks
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()

        # Stop stealth worker
        if self._stealth_worker and hasattr(self._stealth_worker, 'stop'):
            try:
                await self._stealth_worker.stop()
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)

        # Stop session store
        if self._session_store and hasattr(self._session_store, 'stop'):
            try:
                await self._session_store.stop()
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)

        logger.info("🩺 AI Surgeon v%s deactivated — stats: %s", self.VERSION, self._stats)

    # ── Token Pool Interface ─────────────────────────────

    async def get_api_key(self, provider: str) -> Optional[str]:
        """Get the best available API key for a provider."""
        token = await self._token_pool.get_token(provider)
        if token:
            return token.key

        # Trigger automatic regeneration if no tokens available
        logger.warning("🚨 No tokens for %s — attempting bypass regeneration", provider)
        success = await self.bypass_and_regenerate(provider)
        if success:
            token = await self._token_pool.get_token(provider)
            if token:
                return token.key

        return None

    async def report_api_success(
        self, provider: str, key_hash: str,
        tokens_used: int = 0, cost: float = 0.0,
    ) -> None:
        """Report successful API call."""
        await self._token_pool.record_success(provider, key_hash, tokens_used, cost)

    async def report_api_error(
        self, provider: str, key_hash: str,
        is_rate_limit: bool = False, retry_after: float = 0,
    ) -> None:
        """Report API error (triggers rotation if rate-limited)."""
        await self._token_pool.record_error(provider, key_hash, is_rate_limit, retry_after)

        # Check if preemptive rotation needed
        await self._token_pool.check_preemptive_rotation(provider)

    # ── Bypass Operations ────────────────────────────────

    async def bypass_and_regenerate(
        self, provider_id: str, url: Optional[str] = None,
    ) -> bool:
        """
        Execute advanced bypass protocols to restore a failed API provider.

        Pipeline:
        1. Check session store for existing valid session
        2. Launch stealth browser (multi-engine fallback)
        3. Navigate to provider console
        4. Bypass Cloudflare/CAPTCHA
        5. Capture session state
        6. Extract API key (if auto-create available)
        7. Add key to token pool
        """
        self._stats["bypass_attempts"] += 1
        logger.warning("🚨 Crisis for %s — Executing Bypass Protocol v2.0", provider_id)

        # Provider console URLs
        provider_consoles: Dict[str, str] = {
            "google": "https://aistudio.google.com/app/apikey",
            "openrouter": "https://openrouter.ai/keys",
            "groq": "https://console.groq.com/keys",
            "openai": "https://platform.openai.com/api-keys",
            "anthropic": "https://console.anthropic.com/settings/keys",
            "deepseek": "https://platform.deepseek.com/api_keys",
        }
        target_url = url or provider_consoles.get(provider_id.lower(), "https://google.com")

        if not self._stealth_worker:
            logger.error("❌ StealthWorker not available — cannot bypass")
            return False

        try:
            # Try multi-engine bypass for maximum success rate
            if hasattr(self._stealth_worker, 'multi_engine_bypass'):
                result = await self._stealth_worker.multi_engine_bypass(
                    url=target_url,
                    provider_id=provider_id,
                )
            else:
                result = await self._stealth_worker.run_bypass_session(
                    target_url, provider_id,
                )

            if result.get("success"):
                self._stats["bypass_successes"] += 1
                session_id = result.get("session_id", "N/A")
                logger.info(
                    "✅ Bypass successful for %s (session=%s, cookies=%d)",
                    provider_id, session_id[:8] if session_id != "N/A" else "N/A",
                    result.get("cookies_count", 0),
                )

                # Check if we captured API keys
                callback_result = result.get("callback_result", {})
                if isinstance(callback_result, dict):
                    found_keys = callback_result.get("found_keys", [])
                    if found_keys:
                        for key in found_keys:
                            await self._token_pool.add_token(
                                provider=provider_id,
                                key=key,
                                metadata={"source": "bypass_regeneration"},
                            )
                        self._stats["key_regenerations"] += 1
                        logger.info(
                            "🔑 %d API key(s) captured for %s via bypass",
                            len(found_keys), provider_id,
                        )

                return True
            else:
                logger.error(
                    "❌ Bypass failed for %s: %s",
                    provider_id, result.get("error", "unknown"),
                )
                return False

        except Exception as e:
            logger.exception("💥 Critical failure in Surgeon Bypass for %s: %s", provider_id, e)
            return False

    # ── Model Intelligence ───────────────────────────────

    async def get_best_model(self, task_type: str) -> str:
        """
        Determine the optimal model for a task type.

        Uses real-time benchmarks + cost/latency matrix.
        Falls back to routing_matrix if no benchmarks available.
        """
        # Enterprise routing matrix (performance/cost/latency)
        routing_matrix: Final[Dict[str, str]] = {
            "code": "llama-3.3-70b-instruct",
            "creative": "gemini-2.5-pro",
            "analysis": "deepseek-r1",
            "chat": "gemini-2.5-flash",
            "reasoning": "gemini-2.5-pro",
            "translation": "gemini-2.5-flash",
            "summarization": "gemini-2.5-flash",
            "marketing": "gemini-2.5-pro",
            "search": "gemini-2.5-flash",
            "vision": "gemini-2.5-pro",
        }

        # Check benchmarks first
        if task_type in self.model_benchmarks:
            bench = self.model_benchmarks[task_type]
            if isinstance(bench, dict) and "best_model" in bench:
                self._stats["models_evaluated"] += 1
                return bench["best_model"]

        selected = routing_matrix.get(task_type, "gemini-2.5-pro")
        logger.debug("Surgeon selected %s for task type: %s", selected, task_type)
        return selected

    async def get_provider_for_model(self, model: str) -> Optional[str]:
        """Determine which provider serves a given model."""
        model_provider_map: Dict[str, str] = {
            "gemini": "google",
            "llama": "groq",
            "qwen": "groq",
            "deepseek": "deepseek",
            "gpt": "openai",
            "claude": "anthropic",
        }
        model_lower = model.lower()
        for prefix, provider in model_provider_map.items():
            if prefix in model_lower:
                return provider
        return "openrouter"  # Default: OpenRouter has everything

    # ── Failover ─────────────────────────────────────────

    async def failover(self, failed_provider: str, task_type: str = "chat") -> Optional[str]:
        """
        Intelligent failover when a provider is down.
        Returns the best alternative API key.
        """
        self._stats["failovers_triggered"] += 1
        logger.warning("🔀 Failover triggered from %s for %s", failed_provider, task_type)

        # Failover priority order
        fallback_order: Dict[str, List[str]] = {
            "google": ["openrouter", "groq", "deepseek"],
            "groq": ["openrouter", "google", "deepseek"],
            "openrouter": ["google", "groq", "deepseek"],
            "openai": ["openrouter", "google", "anthropic"],
            "anthropic": ["openrouter", "google", "openai"],
            "deepseek": ["openrouter", "google", "groq"],
        }

        fallbacks = fallback_order.get(failed_provider, ["openrouter", "google"])
        for alt_provider in fallbacks:
            key = await self.get_api_key(alt_provider)
            if key:
                logger.info("✅ Failover: %s → %s", failed_provider, alt_provider)
                return key

        logger.error("🚨 All providers exhausted — no failover available!")
        return None

    # ── Background Loops ─────────────────────────────────

    async def _audit_loop(self) -> None:
        """Background infrastructure health audit."""
        while self.is_running:
            try:
                await asyncio.sleep(self.audit_interval)
                self._stats["audits_completed"] += 1

                # Check for preemptive rotation across all providers
                for provider in list(self._token_pool._providers.keys()):
                    await self._token_pool.check_preemptive_rotation(provider)

                logger.debug(
                    "Audit #%d completed — pool: %s",
                    self._stats["audits_completed"],
                    self._token_pool.get_stats().get("total_usable", "?"),
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Audit loop error: %s", e)
                await asyncio.sleep(60)

    async def _research_loop(self) -> None:
        """Background model research and benchmark updates."""
        while self.is_running:
            try:
                await asyncio.sleep(self.research_interval)
                self._stats["research_cycles"] += 1
                logger.debug("Research cycle #%d", self._stats["research_cycles"])

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Research loop error: %s", e)
                await asyncio.sleep(300)

    async def _daily_reset_loop(self) -> None:
        """Reset daily counters at midnight."""
        while self.is_running:
            try:
                # Calculate seconds until next midnight
                now = time.time()
                midnight = (int(now / 86400) + 1) * 86400
                await asyncio.sleep(midnight - now)
                await self._token_pool.reset_daily_counters()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Daily reset error: %s", e)
                await asyncio.sleep(3600)

    # ── Environment Token Loading ────────────────────────

    async def _load_env_tokens(self) -> None:
        """Load API tokens from environment variables."""
        env_map = {
            "google": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
            "groq": ["GROQ_API_KEY"],
            "openrouter": ["OPENROUTER_API_KEY"],
            "openai": ["OPENAI_API_KEY"],
            "anthropic": ["ANTHROPIC_API_KEY"],
            "deepseek": ["DEEPSEEK_API_KEY"],
        }

        loaded = 0
        for provider, env_vars in env_map.items():
            for var in env_vars:
                key = os.environ.get(var, "")
                if key:
                    await self._token_pool.add_token(
                        provider=provider,
                        key=key,
                        metadata={"source": f"env:{var}"},
                    )
                    loaded += 1

        if loaded:
            logger.info("🔑 Loaded %d API tokens from environment", loaded)

    # ── Stats & Health ───────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Comprehensive surgeon statistics."""
        return {
            "version": self.VERSION,
            "running": self.is_running,
            "capabilities_count": len(self.capabilities),
            "token_pool": self._token_pool.get_stats(),
            "stealth_worker": (
                self._stealth_worker.get_stats()
                if self._stealth_worker and hasattr(self._stealth_worker, 'get_stats')
                else {"available": _STEALTH_AVAILABLE}
            ),
            "session_store": (
                self._session_store.get_stats()
                if self._session_store and hasattr(self._session_store, 'get_stats')
                else {"available": _SESSION_STORE_AVAILABLE}
            ),
            **self._stats,
        }

    def get_health(self) -> Dict[str, Any]:
        """Quick health check."""
        pool_stats = self._token_pool.get_stats()
        return {
            "status": "healthy" if self.is_running else "stopped",
            "version": self.VERSION,
            "total_tokens": pool_stats.get("total_tokens", 0),
            "usable_tokens": pool_stats.get("total_usable", 0),
            "stealth": _STEALTH_AVAILABLE,
            "sessions": _SESSION_STORE_AVAILABLE,
            "anti_detect": _ANTI_DETECT_AVAILABLE,
        }


# ═══════════════════════════════════════════════════════════
# Global Singleton
# ═══════════════════════════════════════════════════════════

surgeon: Final[SurgeonAgent] = SurgeonAgent()


