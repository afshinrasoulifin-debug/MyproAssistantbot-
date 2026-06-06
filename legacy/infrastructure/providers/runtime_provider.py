
from __future__ import annotations
"""
RuntimeProvider — Hot-swappable provider that can change at runtime.
"""
import asyncio, logging
from typing import Optional, Any
from arki_project.infrastructure.providers.base import BaseProvider, ProviderRequest, ProviderResponse



logger = logging.getLogger(__name__)

class RuntimeProvider(BaseProvider):
    """Provider that can be swapped at runtime without downtime."""

    def __init__(self, initial: Optional[BaseProvider] = None) -> None:
        super().__init__("runtime", priority=95)
        self._current = initial
        self._lock = asyncio.Lock()
        self._swap_count = 0

    async def swap(self, new_provider: BaseProvider) -> Any:
        async with self._lock:
            old = self._current
            self._current = new_provider
            self._swap_count += 1
            logger.info("RuntimeProvider: swapped %s → %s",
                       old.name if old else "none", new_provider.name)

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        if not self._current:
            return ProviderResponse(success=False, error="No provider configured")
        return await self._current.complete(request)


