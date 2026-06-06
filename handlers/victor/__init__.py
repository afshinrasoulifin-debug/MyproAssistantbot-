
from __future__ import annotations
"""
handlers/victor — Victor v29.0 TITAN PRO
════════════════════════════════════════
"""

# Core Components
from .brain import VictorBrain
from .victor_agent import VictorAgent
from .victor_tools import VictorTools
from .victor_memory import VictorMemory
from .nlp import PersianNLP

# Legacy compatibility (Mocked or real depending on existence)
try:
    from .nlp import PersianTextToolkit
except ImportError:
    PersianTextToolkit = PersianNLP

__all__ = [
    "VictorBrain",
    "VictorAgent",
    "VictorTools",
    "VictorMemory",
    "PersianNLP",
    "PersianTextToolkit"
]


