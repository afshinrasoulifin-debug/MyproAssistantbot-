
"""
multi_llm_orchestrator_pkg/model_result.py — ModelResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ModelResult(TypedDict):
    """Result from querying a single model."""
    model: str
    content: str
    score: int
    duration_ms: int
    success: bool
    error: Optional[str]




