
"""
terminal_emulator_pkg/file_type.py — FileType
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class FileType(Enum):
    """Virtual filesystem entry types."""
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"


# ═══════════════════════════════════════════════════════════════════
# Virtual Filesystem
# ═══════════════════════════════════════════════════════════════════



