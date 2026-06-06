
"""
multi_llm_orchestrator_pkg/routing_config.py — RoutingConfig
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class RoutingConfig:
    """Configuration for model routing."""
    strategy: RoutingStrategy = RoutingStrategy.BALANCED
    max_cost: Optional[float] = None          # USD budget
    max_latency_ms: Optional[float] = None
    min_confidence: Optional[float] = None
    required_capabilities: Optional[List[str]] = None
    preferred_models: Optional[List[str]] = None
    exclude_models: Optional[List[str]] = None


# ═══════════════════════════════════════════════════════════════════
# Model Registry
# ═══════════════════════════════════════════════════════════════════



