
"""
ai_orchestrator — Composed from domain sections
"""
from __future__ import annotations

from .models import AITier, DispatchStrategy, AIProvider, ProviderCallResult, OrchestratorResult, TierConfig  # noqa: F401
from .scoring import AdaptiveScorer, ResponseCache, parse_tier_command  # noqa: F401
from .orchestrator import TitaniumOrchestrator, get_titanium_orchestrator, set_titanium_orchestrator  # noqa: F401
from .routing import ProviderChain, ConsensusEngine, SmartRouter, route  # noqa: F401

__all__ = [
    "AITier",
    "DispatchStrategy",
    "AIProvider",
    "ProviderCallResult",
    "OrchestratorResult",
    "TierConfig",
    "AdaptiveScorer",
    "ResponseCache",
    "parse_tier_command",
    "TitaniumOrchestrator",
    "get_titanium_orchestrator",
    "set_titanium_orchestrator",
    "ProviderChain",
    "ConsensusEngine",
    "SmartRouter",
    "route",
]


