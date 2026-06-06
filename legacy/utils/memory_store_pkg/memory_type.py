
"""
memory_store_pkg/memory_type.py — MemoryType
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class MemoryType(str, Enum):
    CONVERSATION    = "conversation"
    FACT            = "fact"
    PREFERENCE      = "preference"
    SKILL           = "skill"
    RESULT          = "result"
    SUMMARY         = "summary"
    PERSONALITY     = "personality"
    INSTRUCTION     = "instruction"




