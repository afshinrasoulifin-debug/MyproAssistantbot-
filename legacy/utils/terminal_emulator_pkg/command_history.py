
"""
terminal_emulator_pkg/command_history.py — CommandHistory
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class CommandHistory:
    """Searchable command history."""

    def __init__(self, max_size: int = 10000) -> None:
        self.entries: List[CommandEntry] = []
        self.max_size = max_size
        self.position: int = -1

    def add(self, entry: CommandEntry) -> None:
        """Add a command to history."""
        self.entries.append(entry)
        if len(self.entries) > self.max_size:
            self.entries.pop(0)
        self.position = len(self.entries)

    def search(self, pattern: str) -> List[CommandEntry]:
        """Search history by pattern."""
        regex = re.compile(pattern, re.IGNORECASE)
        return [e for e in self.entries if regex.search(e.command)]

    def previous(self) -> Optional[str]:
        """Navigate to previous command."""
        if self.position > 0:
            self.position -= 1
            return self.entries[self.position].command
        return None

    def next(self) -> Optional[str]:
        """Navigate to next command."""
        if self.position < len(self.entries) - 1:
            self.position += 1
            return self.entries[self.position].command
        return None

    def last(self, n: int = 10) -> List[CommandEntry]:
        """Get last n commands."""
        return self.entries[-n:]

    def clear(self) -> None:
        self.entries.clear()
        self.position = -1


# ═══════════════════════════════════════════════════════════════════
# Security Sandbox
# ═══════════════════════════════════════════════════════════════════



