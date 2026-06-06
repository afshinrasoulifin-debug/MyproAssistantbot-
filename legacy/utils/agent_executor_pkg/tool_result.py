
"""
agent_executor_pkg/tool_result.py — ToolResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class ToolResult:
    """Result returned by a tool execution."""
    success: bool
    data: Any
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_cost: int = 0             # estimated tokens consumed
    cached: bool = False

    def truncated_data(self, max_chars: int = MAX_TOOL_OUTPUT_CHARS) -> str:
        """Get JSON-serialized data truncated to max_chars."""
        raw = json.dumps(self.data, ensure_ascii=False, default=str)
        if len(raw) <= max_chars:
            return raw
        return raw[:max_chars] + f"\n... [truncated, {len(raw):,} chars total]"




