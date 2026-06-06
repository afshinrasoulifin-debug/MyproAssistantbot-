
from __future__ import annotations
"""
AutomationLayerRouter — Combines automation-layer + provider-router.
Auto-routes AI requests through layered automation rules.
"""
import asyncio, logging
from typing import Any, Callable, List



logger = logging.getLogger(__name__)

class AutomationRule:
    def __init__(self, name: str, condition: Callable, action: Callable, priority: int = 0) -> None:
        self.name = name
        self.condition = condition
        self.action = action
        self.priority = priority

class AutomationLayerRouter:
    """Layer automation rules on top of provider routing."""

    def __init__(self) -> None:
        self._rules: List[AutomationRule] = []
        self._router = None
        self._pre_hooks: List[Callable] = []
        self._post_hooks: List[Callable] = []

    def set_router(self, router: Any) -> None:
        self._router = router

    def add_rule(self, rule: AutomationRule) -> None:
        self._rules.append(rule)
        self._rules.sort(key=lambda r: -r.priority)

    def add_pre_hook(self, hook: Callable) -> None:
        self._pre_hooks.append(hook)

    def add_post_hook(self, hook: Callable) -> None:
        self._post_hooks.append(hook)

    async def process(self, request: dict) -> dict:
        # Pre-hooks
        for hook in self._pre_hooks:
            request = await hook(request) if asyncio.iscoroutinefunction(hook) else hook(request)

        # Apply automation rules
        for rule in self._rules:
            try:
                if rule.condition(request):
                    request = await rule.action(request) if asyncio.iscoroutinefunction(rule.action) else rule.action(request)
            except Exception as e:
                logger.warning("AutoRule %s failed: %s", rule.name, e)

        # Route to provider
        result = request
        if self._router and hasattr(self._router, 'route'):
            result = await self._router.route(request)

        # Post-hooks
        for hook in self._post_hooks:
            result = await hook(result) if asyncio.iscoroutinefunction(hook) else hook(result)

        return result


