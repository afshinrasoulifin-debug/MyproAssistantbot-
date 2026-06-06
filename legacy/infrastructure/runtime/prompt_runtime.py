
from __future__ import annotations
"""PromptRuntime — Dynamic prompt construction and management."""
import logging
from typing import Dict, List, Any



logger = logging.getLogger(__name__)

class PromptRuntime:
    """Build, version, and manage prompts dynamically."""

    def __init__(self) -> None:
        self._templates: Dict[str, str] = {}
        self._variables: Dict[str, Any] = {}

    def register(self, name: str, template: str) -> Any:
        self._templates[name] = template

    def set_var(self, key: str, value: Any) -> None:
        self._variables[key] = value

    def render(self, name: str, **kwargs) -> str:
        template = self._templates.get(name, "")
        variables = {**self._variables, **kwargs}
        for key, val in variables.items():
            template = template.replace(f"{{{key}}}", str(val))
        return template

    def chain(self, names: List[str], **kwargs) -> str:
        return "\n\n".join(self.render(n, **kwargs) for n in names if n in self._templates)


