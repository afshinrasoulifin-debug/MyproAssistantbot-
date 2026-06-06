
from __future__ import annotations
"""
SmartProvider — Intelligent provider selection based on request analysis.
"""
import logging, re
from typing import Dict, List
from arki_project.infrastructure.providers.base import BaseProvider, ProviderRequest, ProviderResponse



logger = logging.getLogger(__name__)

class SmartProvider(BaseProvider):
    """Routes to optimal provider based on task complexity, user history, cost."""

    def __init__(self) -> None:
        super().__init__("smart", priority=100)
        self._providers: Dict[str, BaseProvider] = {}
        self._task_rules: Dict[str, str] = {}
        self._user_preferences: Dict[int, str] = {}
        self._complexity_patterns = {
            "simple": [r"^.{0,50}$", r"\b(hi|hello|سلام|ممنون)\b"],
            "complex": [r"\b(analyze|research|compare|تحلیل|بررسی)\b", r"```"],
            "code": [r"\b(code|python|function|class|debug)\b"],
            "creative": [r"\b(write|story|poem|بنویس|داستان)\b"],
        }

    def add_provider(self, provider: BaseProvider, tasks: List[str] = None) -> None:
        self._providers[provider.name] = provider
        for task in (tasks or []):
            self._task_rules[task] = provider.name

    def _classify_request(self, request: ProviderRequest) -> str:
        text = " ".join(m.get("content", "") for m in request.messages)
        for category, patterns in self._complexity_patterns.items():
            for pat in patterns:
                if re.search(pat, text, re.IGNORECASE):
                    return category
        return "standard"

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        # Check user preference
        if request.user_id in self._user_preferences:
            pref = self._user_preferences[request.user_id]
            if pref in self._providers and self._providers[pref].is_available:
                return await self._providers[pref].complete(request)

        # Classify and route
        task_type = self._classify_request(request)
        if task_type in self._task_rules:
            target = self._task_rules[task_type]
            if target in self._providers:
                return await self._providers[target].complete(request)

        # Default: best available
        available = sorted(
            [p for p in self._providers.values() if p.is_available],
            key=lambda p: (-p.priority, p.metrics.avg_latency)
        )
        if available:
            return await available[0].complete(request)
        return ProviderResponse(success=False, error="No providers available")


