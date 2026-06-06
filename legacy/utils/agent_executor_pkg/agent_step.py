
"""
agent_executor_pkg/agent_step.py — AgentStep
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class AgentStep:
    """A single step in the agent execution."""
    id: int
    thought: str = ""
    action: Optional[Dict[str, Any]] = None   # {tool, args}
    result: Optional[ToolResult] = None
    observation: str = ""
    duration_ms: float = 0.0
    status: StepStatus = StepStatus.PENDING
    retries: int = 0
    depends_on: List[int] = field(default_factory=list)
    error_trace: str = ""
    cost: float = 0.0

    @property
    def tool_name(self) -> Optional[str]:
        return self.action.get("tool") if self.action else None

    @property
    def tool_args(self) -> dict:
        return self.action.get("args", {}) if self.action else {}




