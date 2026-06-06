
"""
api_builder_pkg/model_tier.py — ModelTier
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ModelTier(str, Enum):
    AUTO = "auto"           # SmartClient selects
    FAST = "fast"           # Fast models (Gemini Flash, etc.)
    PRO = "pro"             # Pro models (Gemini Pro, GPT-4o)
    ULTRA = "ultra"         # Ultra models (Grok-4, Claude Opus 4)
    CONSORTIUM = "consortium"  # Multi-model hive-mind




