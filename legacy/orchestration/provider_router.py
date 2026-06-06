
from __future__ import annotations
"""
arki_project/orchestration/provider_router.py — Smart Provider Router
═══════════════════════════════════════════════════════════════
Routes inference requests to the optimal provider based on capabilities, health, and cost.

Author: Manus AI
"""


import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Final, Tuple

from .types import (
    InferenceRequest,
    ProviderHealth,
    ProviderName,
    ProviderStatus,
)

# Configure logging
logger = logging.getLogger("arki.orchestration.provider_router")

# ── TITANIUM v29.0 Integration ──
try:
    _TITANIUM_ACTIVE: Final[bool] = True
except ImportError:
    _TITANIUM_ACTIVE: Final[bool] = False


@dataclass(slots=True)
class ProviderCapability:
    """
    Defines the technical and economic capabilities of an AI provider.
    
    Attributes:
        name (ProviderName): The provider identifier.
        models (Dict[str, str]): Mapping of model keys to provider-specific IDs.
        max_tokens (int): Maximum token limit for context.
        supports_tools (bool): Whether function calling is supported.
        supports_streaming (bool): Whether streaming responses are supported.
        cost_per_1k_tokens (float): Economic cost factor for routing decisions.
        priority (int): Base preference level (higher is better).
    """
    name: ProviderName
    models: Dict[str, str]
    max_tokens: int = 65536
    supports_tools: bool = False
    supports_streaming: bool = True
    cost_per_1k_tokens: float = 0.0
    priority: int = 0


@dataclass(slots=True)
class RoutingDecision:
    """
    The outcome of a routing operation.
    
    Attributes:
        providers (List[ProviderName]): Ordered list of providers to attempt.
        model_ids (Dict[ProviderName, str]): Mapping of provider to specific model ID.
        reason (str): Justification for the routing decision.
    """
    providers: List[ProviderName]
    model_ids: Dict[ProviderName, str]
    reason: str = ""


class ProviderRouter:
    """
    Intelligent router that selects the best provider(s) for a given request.
    
    Implements multi-factor scoring including:
    - Model availability
    - Real-time health and circuit breaker status
    - Latency and error rate history
    - Cost optimization
    - User sticky sessions
    """

    def __init__(self) -> None:
        """Initializes the ProviderRouter with default fallback order."""
        self._capabilities: Dict[ProviderName, ProviderCapability] = {}
        self._health: Dict[ProviderName, ProviderHealth] = {}
        self._user_sticky: Dict[int, ProviderName] = {}
        self._fallback_order: List[ProviderName] = [
            ProviderName.GEMINI,
            ProviderName.GROQ,
            ProviderName.OPENROUTER,
        ]

    def register_provider(self, cap: ProviderCapability) -> None:
        """
        Registers a provider and its capabilities.
        
        Args:
            cap (ProviderCapability): The capability definition to register.
        """
        self._capabilities[cap.name] = cap
        if cap.name not in self._health:
            self._health[cap.name] = ProviderHealth(name=cap.name)
        logger.info(
            f"Provider registered: {cap.name.value} ({len(cap.models)} models, priority={cap.priority})"
        )

    def update_health(self, health: ProviderHealth) -> None:
        """Updates the health state for a specific provider."""
        self._health[health.name] = health

    def set_fallback_order(self, order: Sequence[ProviderName]) -> None:
        """Overrides the default fallback sequence."""
        self._fallback_order = list(order)

    def route(self, request: InferenceRequest) -> RoutingDecision:
        """
        Selects an ordered list of providers for the given request.
        
        Args:
            request (InferenceRequest): The request details.
            
        Returns:
            RoutingDecision: The ordered providers and their respective model IDs.
        """
        model_key: str = request.model_key
        candidates: List[Tuple[ProviderName, str, float]] = []

        for name, cap in self._capabilities.items():
            # 1. Verify model support
            model_id = cap.models.get(model_key)
            if not model_id:
                continue

            # 2. Check health status
            health = self._health.get(name)
            if health and health.status == ProviderStatus.DOWN:
                continue

            # 3. Calculate score (lower is better)
            score = self._score_provider(name, cap, health, request)
            candidates.append((name, model_id, score))

        if not candidates:
            return self._fallback_decision(request)

        # Sort candidates by calculated score
        candidates.sort(key=lambda x: x[2])

        providers = [c[0] for c in candidates]
        model_ids = {c[0]: c[1] for c in candidates}

        return RoutingDecision(
            providers=providers,
            model_ids=model_ids,
            reason=f"scored: {', '.join(f'{c[0].value}={c[2]:.1f}' for c in candidates)}",
        )

    def _score_provider(
        self,
        name: ProviderName,
        cap: ProviderCapability,
        health: Optional[ProviderHealth],
        request: InferenceRequest,
    ) -> float:
        """
        Calculates a routing score for a provider.
        
        Score components:
        - Base priority: -10 per priority level.
        - Latency: +1 per 100ms (max 30).
        - Error rate: +50 penalty for high error rates.
        - Status: +20 for DEGRADED, +100 for open circuit.
        - Cost: +10 per unit cost.
        - Sticky: -5 bonus for user's preferred provider.
        """
        score: float = 100.0 - cap.priority * 10

        if health:
            # Latency penalty
            score += min(health.avg_latency_ms / 100, 30)

            # Error rate penalty
            if health.total_requests > 10:
                error_rate = 1.0 - health.success_rate
                score += error_rate * 50

            # Status penalties
            if health.status == ProviderStatus.DEGRADED:
                score += 20
            if health.circuit_open:
                score += 100

        # Economic cost factor
        score += cap.cost_per_1k_tokens * 10

        # Sticky session bonus
        if request.user_id and self._user_sticky.get(request.user_id) == name:
            score -= 5

        return score

    def _fallback_decision(self, request: InferenceRequest) -> RoutingDecision:
        """Generates a fallback routing decision when specific model is unavailable."""
        providers: List[ProviderName] = []
        model_ids: Dict[ProviderName, str] = {}

        for name in self._fallback_order:
            cap = self._capabilities.get(name)
            health = self._health.get(name)
            if health and health.status == ProviderStatus.DOWN:
                continue
            if cap:
                # Select first available model from the provider
                first_model = next(iter(cap.models.values()), None)
                if first_model:
                    providers.append(name)
                    model_ids[name] = first_model

        return RoutingDecision(
            providers=providers,
            model_ids=model_ids,
            reason="fallback (requested model not found)",
        )

    def record_success(self, provider: ProviderName, user_id: int = 0) -> None:
        """Records a successful interaction to maintain sticky sessions."""
        if user_id:
            self._user_sticky[user_id] = provider
            # Maintain sticky map size
            if len(self._user_sticky) > 50_000:
                keys = list(self._user_sticky.keys())
                for k in keys[:25_000]:
                    del self._user_sticky[k]

    def get_capabilities(self) -> Dict[ProviderName, ProviderCapability]:
        """Returns the registered capabilities for all providers."""
        return dict(self._capabilities)

    def get_health_map(self) -> Dict[ProviderName, ProviderHealth]:
        """Returns the current health status map."""
        return dict(self._health)


