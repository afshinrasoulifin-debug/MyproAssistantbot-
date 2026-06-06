
from __future__ import annotations
"""
PromptRuntimeOptimizer — Combines prompt runtime + optimization engine.
"""
import logging, re
from typing import Any



logger = logging.getLogger(__name__)

class PromptRuntimeOptimizer:
    """Dynamic prompt construction with automatic optimization."""

    def __init__(self) -> None:
        self._templates: dict = {}
        self._optimizations: list = []

    def register(self, name: str, template: str) -> Any:
        self._templates[name] = template

    def add_optimization(self, fn: Any) -> None:
        self._optimizations.append(fn)

    def build(self, name: str, **kwargs) -> str:
        template = self._templates.get(name, "")
        for key, val in kwargs.items():
            template = template.replace(f"{{{key}}}", str(val))
        # Auto-optimize
        template = re.sub(r"\n{3,}", "\n\n", template)
        template = re.sub(r" {2,}", " ", template)
        for opt in self._optimizations:
            template = opt(template)
        return template.strip()


