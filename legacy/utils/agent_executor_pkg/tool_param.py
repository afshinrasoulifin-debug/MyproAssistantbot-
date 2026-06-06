
"""
agent_executor_pkg/tool_param.py — ToolParam
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class ToolParam:
    """Describes a single parameter for a tool."""
    name: str
    type: str                       # string | number | boolean | array | object
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def to_schema(self) -> dict:
        """Convert to OpenAI-compatible JSON Schema property."""
        schema: dict = {"type": self.type, "description": self.description}
        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        if self.min_value is not None:
            schema["minimum"] = self.min_value
        if self.max_value is not None:
            schema["maximum"] = self.max_value
        return schema




