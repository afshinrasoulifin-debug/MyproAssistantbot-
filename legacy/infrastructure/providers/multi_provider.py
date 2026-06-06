
from __future__ import annotations
"""
MultiProvider — Fan-out to multiple providers, aggregate results.
"""
import asyncio, logging
from typing import Dict, Any
from arki_project.infrastructure.providers.base import BaseProvider, ProviderRequest, ProviderResponse



logger = logging.getLogger(__name__)

class MultiProvider(BaseProvider):
    """Send request to ALL providers and aggregate/select best response."""

    def __init__(self, strategy: str = "fastest") -> None:
        super().__init__("multi", priority=80)
        self._providers: Dict[str, BaseProvider] = {}
        self._strategy = strategy  # fastest, best_quality, consensus, all

    def add(self, provider: BaseProvider) -> Any:
        self._providers[provider.name] = provider

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        available = [p for p in self._providers.values() if p.is_available]
        if not available:
            return ProviderResponse(success=False, error="No providers")

        tasks = {p.name: asyncio.create_task(p.complete(request)) for p in available}

        if self._strategy == "fastest":
            done, pending = await asyncio.wait(tasks.values(), return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
            result = done.pop().result()
            result.metadata["strategy"] = "fastest"
            return result

        # Wait for all
        results = {}
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception as e:
                results[name] = ProviderResponse(success=False, error=str(e))

        successful = {k: v for k, v in results.items() if v.success}
        if not successful:
            return ProviderResponse(success=False, error="All providers failed")

        if self._strategy == "best_quality":
            best = max(successful.values(), key=lambda r: len(r.content))
            best.metadata["strategy"] = "best_quality"
            return best

        # Default: return first successful
        first = list(successful.values())[0]
        first.metadata["all_results"] = len(successful)
        return first


