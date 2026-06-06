
from __future__ import annotations
"""
ProviderPoolShadow — Combines provider pool + shadow testing.
Pool of providers with A/B shadow testing on a sample of requests.
"""
import asyncio, logging
try:
    from arki_project.utils.titanium.compat import secure_random as random
except ImportError:
    import random
from typing import Any



logger = logging.getLogger(__name__)

class ProviderPoolShadow:
    """Provider pool with built-in shadow comparison testing."""

    def __init__(self, shadow_rate: float = 0.05) -> None:
        self._primary_pool = None
        self._shadow_pool = None
        self._shadow_rate = shadow_rate
        self._comparisons: list = []

    def set_pools(self, primary: Any, shadow: Any) -> None:
        self._primary_pool = primary
        self._shadow_pool = shadow

    async def execute(self, request: Any, strategy: str = "best") -> Any:
        primary_result = await self._primary_pool.execute(request, strategy) if self._primary_pool else None

        if random.random() < self._shadow_rate and self._shadow_pool:
            _t = asyncio.create_task(self._shadow_test(request, strategy))
            _t.add_done_callback(lambda t: logger.error('Task failed: %s', t.exception()) if t.done() and not t.cancelled() and t.exception() else None)

        return primary_result

    async def _shadow_test(self, request: Any, strategy: str) -> Any:
        try:
            shadow_result = await self._shadow_pool.execute(request, strategy)
            self._comparisons.append(shadow_result)
        except Exception as _exc:
            logger.debug("Suppressed: %s", _exc)


