
"""
agent_executor_pkg/agent_config.py — AgentConfig
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class AgentConfig:
    """Configuration for an agent execution."""
    model: str = "anthropic/claude-sonnet-4-20250514"
    api_key: str = ""
    max_steps: int = MAX_AGENT_STEPS
    max_time_s: float = MAX_TOTAL_TIME_S
    max_tokens: int = 4096
    max_cost: float = 1.0           # USD budget
    temperature: float = 0.3
    tools_filter: Optional[List[str]] = None   # restrict to these tools
    enable_reflection: bool = True
    enable_parallel: bool = True
    enable_caching: bool = True
    streaming: bool = False
    verbose: bool = False
    memory_context: str = ""        # injected RAG context
    system_prompt_extra: str = ""   # additional system instructions

    # Callbacks
    on_step: Optional[Callable[[AgentStep], None]] = None
    on_thought: Optional[Callable[[str], None]] = None
    on_tool_call: Optional[Callable[[str, dict], None]] = None
    on_tool_result: Optional[Callable[[str, ToolResult], None]] = None
    on_plan: Optional[Callable[[AgentPlan], None]] = None
    on_reflection: Optional[Callable[[str, float], None]] = None


# ═══════════════════════════════════════════════════════════════════
# LRU Cache with TTL
# ═══════════════════════════════════════════════════════════════════



