
"""
ai_client_pkg/chat_message.py — ChatMessage
Arki Engine v29.0.0
"""
from __future__ import annotations
from ._base import *  # noqa

@dataclass(slots=True)
class ChatMessage:
    role: str        # "user" | "model" | "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════════
# v10: Smart Model Selection & Adaptive Temperature
# ═══════════════════════════════════════════════════════════════════



