
"""
agent_executor_pkg/trace_status.py — TraceStatus
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class TraceStatus(str, Enum):
    PLANNING    = "planning"
    EXECUTING   = "executing"
    REFLECTING  = "reflecting"
    COMPLETED   = "completed"
    ERROR       = "error"
    TIMEOUT     = "timeout"
    CANCELLED   = "cancelled"


# ═══════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════



