
"""
workflow_engine_pkg/edge_type.py — EdgeType
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class EdgeType(Enum):
    """Edge types for workflow connections."""
    NORMAL = "normal"
    CONDITIONAL_TRUE = "conditional_true"
    CONDITIONAL_FALSE = "conditional_false"
    ERROR = "error"
    ALWAYS = "always"


# ═══════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════



