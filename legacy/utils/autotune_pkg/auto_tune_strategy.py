
"""
autotune_pkg/auto_tune_strategy.py — AutoTuneStrategy
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class AutoTuneStrategy(str, Enum):
    """Available tuning strategies."""
    PRECISE = "precise"
    BALANCED = "balanced"
    CREATIVE = "creative"
    CHAOTIC = "chaotic"
    ADAPTIVE = "adaptive"  # Uses context detection




