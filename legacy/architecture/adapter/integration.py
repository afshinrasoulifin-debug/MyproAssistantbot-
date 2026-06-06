
from __future__ import annotations
"""
architecture.adapter.integration — IntegrationAdapter, CompatibilityAdapter
══════════════════════════════════════════════════════════════════════════
Adapters for third-party service integration.
Covers: integration-adapter, compatibility-adapter
"""
import logging
from typing import Any, Callable, Dict



logger = logging.getLogger(__name__)

class IntegrationAdapter:
    """Adapter for integrating external services."""
    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
        self._transformers: Dict[str, Callable] = {}

    def register_transformer(self, name: str, fn: Callable) -> None:
        self._transformers[name] = fn

    def transform(self, name: str, data: Any) -> Any:
        fn = self._transformers.get(name)
        if fn:
            return fn(data)
        return data

    def to_internal(self, external_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.transform("to_internal", external_data)

    def to_external(self, internal_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.transform("to_external", internal_data)

class CompatibilityAdapter(IntegrationAdapter):
    """Adapter ensuring backward compatibility between versions."""
    def __init__(self, target_version: str = "7.0") -> None:
        super().__init__(f"compat-v{target_version}")
        self.target_version = target_version
        self._mappings: Dict[str, str] = {}

    def map_field(self, old_name: str, new_name: str) -> None:
        self._mappings[old_name] = new_name

    def adapt(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, val in data.items():
            new_key = self._mappings.get(key, key)
            result[new_key] = val
        return result


