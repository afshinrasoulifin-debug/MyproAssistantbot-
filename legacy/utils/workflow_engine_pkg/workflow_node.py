
"""
workflow_engine_pkg/workflow_node.py — WorkflowNode
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class WorkflowNode:
    """A single node in the workflow DAG."""
    id: str
    name: str
    node_type: NodeType
    config: NodeConfig = field(default_factory=NodeConfig)
    handler: Optional[str] = None  # function/tool name
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Execution state
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    attempt: int = 0

    def duration(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value,
            "handler": self.handler,
            "parameters": self.parameters,
            "status": self.status_code.value,
            "result": self.result,
            "error": self.error,
            "attempt": self.attempt,
            "config": {
                "timeout_seconds": self.config.timeout_seconds,
                "cache_result": self.config.cache_result,
                "skip_on_error": self.config.skip_on_error,
            },
        }




