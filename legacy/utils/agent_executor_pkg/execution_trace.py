
"""
agent_executor_pkg/execution_trace.py — ExecutionTrace
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class ExecutionTrace:
    """Full trace of an agent execution for auditing."""
    id: str = field(default_factory=lambda: f"trace_{uuid.uuid4().hex[:12]}")
    query: str = ""
    plan: Optional[AgentPlan] = None
    steps: List[AgentStep] = field(default_factory=list)
    final_answer: str = ""
    reflection: str = ""
    total_duration_ms: float = 0.0
    tokens_used: int = 0
    tool_calls: int = 0
    total_cost: float = 0.0
    success: bool = False
    model: str = ""
    status: TraceStatus = TraceStatus.PLANNING
    metadata: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        """Human-readable summary of the trace."""
        lines = [
            f"Trace {self.id} | {self.status.value}",
            f"Query: {self.query[:120]}",
            f"Steps: {len(self.steps)} | Tools: {self.tool_calls}",
            f"Duration: {self.total_duration_ms:.0f}ms | Cost: ${self.total_cost:.4f}",
            f"Tokens: {self.tokens_used:,}",
        ]
        if self.reflection:
            lines.append(f"Reflection: {self.reflection[:200]}")
        return "\n".join(lines)




