
"""
models_registry_pkg/libertas_combo_id.py — LibertasComboId
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class LibertasComboId(str, Enum):
    """Available L1B3RT4S combo identifiers."""
    GROK_420 = "grok-420"
    GEMINI_RESET = "gemini-reset"
    GPT_CLASSIC = "gpt-classic"
    CLAUDE_INVERSION = "claude-inversion"
    HERMES_FAST = "hermes-fast"



