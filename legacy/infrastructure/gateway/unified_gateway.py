
from __future__ import annotations
"""UnifiedGateway — Single API surface for all AI providers."""
import logging
from typing import Dict, Any
from arki_project.infrastructure.gateway.ai_gateway import AIGateway, GatewayRequest, GatewayResponse



logger = logging.getLogger(__name__)

class UnifiedGateway(AIGateway):
    """Extends AIGateway with provider normalization — all providers share one interface."""

    def __init__(self) -> None:
        super().__init__()
        self._provider_map: Dict[str, str] = {}

    def map_provider(self, model_prefix: str, provider: str) -> Any:
        self._provider_map[model_prefix] = provider

    def resolve_provider(self, model: str) -> str:
        for prefix, provider in self._provider_map.items():
            if model.startswith(prefix):
                return provider
        return "default"

    async def process(self, request: GatewayRequest) -> GatewayResponse:
        request.metadata["resolved_provider"] = self.resolve_provider(request.model)
        return await super().process(request)


