
"""
multi_llm_orchestrator_pkg/task_profile.py — TaskProfile
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class TaskProfile:
    category: str
    required_strengths: List[str]
    complexity: str                     # low | medium | high
    needs_vision: bool
    needs_tools: bool
    estimated_tokens: int

# Rule-based classifier using regex patterns


