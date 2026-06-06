
"""
openrouter_client_pkg/chat_message.py — ChatMessage
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class ChatMessage:
    """Chat message."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.name:
            d["name"] = self.name
        if self.function_call:
            d["function_call"] = self.function_call
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        return d




