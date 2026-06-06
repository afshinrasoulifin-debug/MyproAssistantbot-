
from __future__ import annotations
"""
ModelRouterRegistry — Combines model routing + model registry.
"""
import logging
from typing import Dict, Any



logger = logging.getLogger(__name__)

class ModelRouterRegistry:
    """Registry of all models with intelligent routing."""

    def __init__(self) -> None:
        self._models: Dict[str, Dict[str, Any]] = {}
        self._route_rules: Dict[str, str] = {}

    def register_model(self, name: str, provider: str, capabilities: list = None, **meta) -> None:
        self._models[name] = {
            "provider": provider,
            "capabilities": capabilities or [],
            **meta
        }

    def add_route(self, task_type: str, model: str) -> None:
        self._route_rules[task_type] = model

    def route(self, task_type: str) -> str:
        return self._route_rules.get(task_type, "gemini-pro")

    def get_model_info(self, name: str) -> Dict:
        return self._models.get(name, {})

    def list_all(self) -> Dict[str, Dict]:
        return dict(self._models)


