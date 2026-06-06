
"""
multi_llm_orchestrator_pkg/routing_strategy.py — RoutingStrategy
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class RoutingStrategy(str, Enum):
    BEST_QUALITY = "best_quality"
    CHEAPEST     = "cheapest"
    FASTEST      = "fastest"
    BALANCED     = "balanced"
    SPECIALIST   = "specialist"




