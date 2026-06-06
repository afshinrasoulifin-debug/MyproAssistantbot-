
"""
multi_llm_orchestrator_pkg/consortium_synthesis.py — ConsortiumSynthesis
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ConsortiumSynthesis(TypedDict):
    """Result from CONSORTIUM synthesis."""
    synthesis: str
    orchestrator_model: str
    duration_ms: int




