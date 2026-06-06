
"""
models_registry_pkg/godmode_param_key.py — GodmodeParamKey
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class GodmodeParamKey(str, Enum):
    """Valid parameter keys for APEX boost."""
    TEMPERATURE = "temperature"
    PRESENCE_PENALTY = "presence_penalty"
    FREQUENCY_PENALTY = "frequency_penalty"
    TOP_P = "top_p"
    TOP_K = "top_k"
    REPETITION_PENALTY = "repetition_penalty"



