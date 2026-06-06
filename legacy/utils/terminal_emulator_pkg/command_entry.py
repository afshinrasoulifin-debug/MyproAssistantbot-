
"""
terminal_emulator_pkg/command_entry.py — CommandEntry
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class CommandEntry:
    """Record of an executed command."""
    command: str
    language: Language
    output: str
    error: str = ""
    exit_code: int = 0
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0




