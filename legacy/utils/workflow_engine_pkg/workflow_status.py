
"""
workflow_engine_pkg/workflow_status.py — WorkflowStatus
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class WorkflowStatus(Enum):
    """Overall workflow status."""
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"




