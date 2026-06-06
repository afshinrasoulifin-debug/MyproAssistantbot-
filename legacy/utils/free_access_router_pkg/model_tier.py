
"""
free_access_router_pkg/model_tier.py — ModelTier
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ModelTier(Enum):
    """Model importance tier — affects routing strategy."""
    CRITICAL = "critical"   # Flagship models (GPT-4o, Claude, Gemini Pro) → concurrent race
    STANDARD = "standard"   # Regular models → sequential fallback
    ECONOMY = "economy"     # Small/fast models → single best route




