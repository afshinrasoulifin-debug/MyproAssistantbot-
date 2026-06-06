
"""
agent_executor_pkg/tool.py — Tool
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class Tool:
    """A callable tool available to the agent."""
    name: str
    description: str
    parameters: List[ToolParam]
    execute: Callable[..., Awaitable[ToolResult]]
    category: ToolCategory = ToolCategory.UTILITY
    requires_api_key: bool = False
    timeout_s: float = DEFAULT_TOOL_TIMEOUT_S
    cost_per_call: float = 0.0      # estimated USD
    tags: List[str] = field(default_factory=list)

    def to_openai_tool(self) -> dict:
        """Convert to OpenAI function-calling tool definition."""
        properties = {}
        required = []
        for p in self.parameters:
            properties[p.name] = p.to_schema()
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }




