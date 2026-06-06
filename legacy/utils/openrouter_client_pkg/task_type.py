
"""
openrouter_client_pkg/task_type.py — TaskType
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class TaskType(Enum):
    CHAT = "chat"
    CODE = "code"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    SUMMARIZE = "summarize"
    TRANSLATE = "translate"
    REASONING = "reasoning"
    FUNCTION = "function"




