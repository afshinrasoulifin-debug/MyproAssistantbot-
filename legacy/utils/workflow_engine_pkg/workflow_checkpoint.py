
"""
workflow_engine_pkg/workflow_checkpoint.py — WorkflowCheckpoint
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class WorkflowCheckpoint:
    """Snapshot of workflow state for resume capability."""
    workflow_id: str
    timestamp: float
    node_states: Dict[str, Dict[str, Any]]
    variables: Dict[str, Any]
    completed_nodes: List[str]

    def to_json(self) -> str:
        return json.dumps({
            "workflow_id": self.workflow_id,
            "timestamp": self.timestamp,
            "node_states": self.node_states,
            "variables": self.variables,
            "completed_nodes": self.completed_nodes,
        })

# ── TITANIUM v29.0 Integration ──


    @classmethod
    def from_json(cls, data: str) -> "WorkflowCheckpoint":
        d = json.loads(data)
        return cls(**d)


# ═══════════════════════════════════════════════════════════════════
# Expression Evaluator (Safe)
# ═══════════════════════════════════════════════════════════════════



