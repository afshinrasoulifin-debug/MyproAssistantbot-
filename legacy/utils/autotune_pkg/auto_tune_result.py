
"""
autotune_pkg/auto_tune_result.py — AutoTuneResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class AutoTuneResult(TypedDict):
    """Complete result from apex_compute_autotune."""
    params: AutoTuneParams
    detected_context: str
    confidence: float
    reasoning: str


# ═══════════════════ STRATEGY PROFILES ═══════════════════
# Fixed presets for non-adaptive strategies.



