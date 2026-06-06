
from __future__ import annotations
"""
FallbackProvider — Cascading fallback chain with automatic failover.
"""
import logging, time
from typing import List, Any
from arki_project.infrastructure.providers.base import BaseProvider, ProviderRequest, ProviderResponse



logger = logging.getLogger(__name__)

class FallbackProvider(BaseProvider):
    """Try providers in order; on failure, cascade to next."""

    def __init__(self, chain: List[BaseProvider] = None) -> None:
        super().__init__("fallback", priority=90)
        self._chain: List[BaseProvider] = chain or []

    def add(self, provider: BaseProvider) -> Any:
        self._chain.append(provider)

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        errors = []
        for provider in self._chain:
            if not provider.is_available:
                continue
            try:
                t0 = time.time()
                resp = await provider.complete(request)
                if resp.success:
                    resp.metadata["fallback_attempts"] = len(errors)
                    return resp
                errors.append(f"{provider.name}: {resp.error}")
            except Exception as e:
                errors.append(f"{provider.name}: {e}")
                logger.warning("Fallback: %s failed (%s), trying next", provider.name, e)

        return ProviderResponse(
            success=False,
            error=f"All providers failed: {'; '.join(errors)}",
            metadata={"attempts": len(errors)}
        )


