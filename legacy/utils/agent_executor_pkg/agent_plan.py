
"""
agent_executor_pkg/agent_plan.py — AgentPlan
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class AgentPlan:
    """Decomposition of a user query into executable steps."""
    goal: str
    steps: List[Dict[str, Any]]     # [{description, tool, args, depends_on}]
    reasoning: str = ""
    complexity: str = "medium"      # low | medium | high | expert
    estimated_time_s: float = 30.0
    estimated_cost: float = 0.0




