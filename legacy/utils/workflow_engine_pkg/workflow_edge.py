
"""
workflow_engine_pkg/workflow_edge.py — WorkflowEdge
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class WorkflowEdge:
    """Connection between two nodes."""
    source: str
    target: str
    edge_type: EdgeType = EdgeType.NORMAL
    condition: Optional[str] = None
    transform: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type.value,
            "condition": self.condition,
            "transform": self.transform,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WorkflowEdge":
        return cls(
            source=d["source"],
            target=d["target"],
            edge_type=EdgeType(d.get("edge_type", "normal")),
            condition=d.get("condition"),
            transform=d.get("transform"),
        )




