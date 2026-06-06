
"""
models_registry_pkg/persona.py — Persona
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass(frozen=True, slots=True)
class Persona:
    name: str
    system_prompt: str



