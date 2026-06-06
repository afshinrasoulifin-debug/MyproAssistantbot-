
"""
workflow_engine_pkg/node_type.py — NodeType
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class NodeType(Enum):
    """Types of workflow nodes."""
    TASK = "task"
    CONDITION = "condition"
    SWITCH = "switch"
    LOOP = "loop"
    FOR_EACH = "for_each"
    PARALLEL = "parallel"
    MERGE = "merge"
    DELAY = "delay"
    WEBHOOK = "webhook"
    SUB_WORKFLOW = "sub_workflow"
    TRANSFORM = "transform"
    CHECKPOINT = "checkpoint"




