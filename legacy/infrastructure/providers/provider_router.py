
from __future__ import annotations
"""
ProviderRouter — Rule-based routing of requests to providers.
"""
import logging
from typing import Any, Callable, Dict, List, Optional
from arki_project.infrastructure.providers.base import BaseProvider, ProviderRequest, ProviderResponse



logger = logging.getLogger(__name__)

class RoutingRule:
    def __init__(self, name: str, condition: Callable[[ProviderRequest], bool], target: str, priority: int = 0) -> None:
        self.name = name
        self.condition = condition
        self.target = target
        self.priority = priority

class ProviderRouter(BaseProvider):
    """Route requests to providers based on configurable rules."""

    def __init__(self) -> None:
        super().__init__("router", priority=100)
        self._providers: Dict[str, BaseProvider] = {}
        self._rules: List[RoutingRule] = []
        self._default: Optional[str] = None

    def register(self, provider: BaseProvider) -> Any:
        self._providers[provider.name] = provider

    def add_rule(self, rule: RoutingRule) -> None:
        self._rules.append(rule)
        self._rules.sort(key=lambda r: -r.priority)

    def set_default(self, name: str) -> None:
        self._default = name

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        for rule in self._rules:
            try:
                if rule.condition(request):
                    if rule.target in self._providers:
                        return await self._providers[rule.target].complete(request)
            except Exception:
                continue

        if self._default and self._default in self._providers:
            return await self._providers[self._default].complete(request)

        return ProviderResponse(success=False, error="No matching route")


