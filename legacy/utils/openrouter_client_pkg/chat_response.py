
"""
openrouter_client_pkg/chat_response.py — ChatResponse
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class ChatResponse:
    """Chat completion response."""
    model: str
    content: str
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=dict)
    cost: float = 0.0
    latency_ms: float = 0.0
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "finish_reason": self.finish_reason,
            "usage": self.usage,
            "cost": round(self.cost, 6),
            "latency_ms": round(self.latency_ms, 2),
        }


# ═══════════════════════════════════════════════════════════════════
# Cost Tracker
# ═══════════════════════════════════════════════════════════════════



