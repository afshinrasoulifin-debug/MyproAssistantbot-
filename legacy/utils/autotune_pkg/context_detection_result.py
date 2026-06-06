
"""
autotune_pkg/context_detection_result.py — ContextDetectionResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ContextDetectionResult(NamedTuple):
    """Result from context detection."""
    context_type: str
    confidence: float
    all_scores: Dict[str, int]




