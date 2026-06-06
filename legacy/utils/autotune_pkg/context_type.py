
"""
autotune_pkg/context_type.py — ContextType
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ContextType(str, Enum):
    """Detectable conversation context types (5 from APEX spec)."""
    CODE = "code"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    CONVERSATIONAL = "conversational"
    CHAOTIC = "chaotic"




