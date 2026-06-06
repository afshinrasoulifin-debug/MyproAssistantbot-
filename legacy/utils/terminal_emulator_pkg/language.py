
"""
terminal_emulator_pkg/language.py — Language
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class Language(Enum):
    """Supported execution languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"
    AUTO = "auto"




