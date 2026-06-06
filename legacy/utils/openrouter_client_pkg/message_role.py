
"""
openrouter_client_pkg/message_role.py — MessageRole
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


# ═══════════════════════════════════════════════════════════════════
# Model Registry
# ═══════════════════════════════════════════════════════════════════



