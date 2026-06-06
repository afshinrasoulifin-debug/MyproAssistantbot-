
"""
autotune_pkg/auto_tune_params.py — AutoTuneParams
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class AutoTuneParams(TypedDict, total=False):
    """Parameter set for model generation."""
    temperature: float
    top_p: float
    top_k: int
    frequency_penalty: float
    presence_penalty: float
    repetition_penalty: float




