
"""
terminal_emulator_pkg/process_info.py — ProcessInfo
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class ProcessInfo:
    """Information about a running process."""
    pid: int
    command: str
    language: Language
    state: ProcessState = ProcessState.RUNNING
    output: str = ""
    error: str = ""
    exit_code: Optional[int] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    memory_used: int = 0




