
"""
models_registry_pkg/model_info.py — ModelInfo
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass(frozen=True, slots=True)
class ModelInfo:
    id: str
    name: str
    emoji: str
    provider: str  # "gemini" | "groq"
    desc: str
    ctx: str



