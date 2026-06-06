
"""
terminal_emulator_pkg/process_state.py — ProcessState
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ProcessState(Enum):
    """Process execution states."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"
    SUSPENDED = "suspended"




