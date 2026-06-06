
"""
terminal_emulator_pkg/terminal_session.py — TerminalSession
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class TerminalSession:
    """A complete terminal session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    language: Language = Language.AUTO
    cwd: str = "/home"
    env: Dict[str, str] = field(default_factory=dict)
    aliases: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    max_output_lines: int = 1000


# ═══════════════════════════════════════════════════════════════════
# Terminal Emulator (Main Interface)
# ═══════════════════════════════════════════════════════════════════



