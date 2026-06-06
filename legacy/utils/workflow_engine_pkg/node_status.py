
"""
workflow_engine_pkg/node_status.py — NodeStatus
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class NodeStatus(Enum):
    """Execution status of a node."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    WAITING = "waiting"




