
"""
agent_executor_pkg/step_status.py — StepStatus
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class StepStatus(str, Enum):
    PENDING     = "pending"
    QUEUED      = "queued"
    RUNNING     = "running"
    COMPLETED   = "completed"
    FAILED      = "failed"
    SKIPPED     = "skipped"
    RETRYING    = "retrying"
    CANCELLED   = "cancelled"




