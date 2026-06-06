
from __future__ import annotations
"""
ShadowProvider — Run requests against shadow provider for A/B comparison.
"""
import asyncio, logging, time
from arki_project.infrastructure.providers.base import BaseProvider, ProviderRequest, ProviderResponse

logger = logging.getLogger(__name__)

class ShadowProvider(BaseProvider):
    """Send requests to primary AND shadow; return primary, log shadow for comparison."""

    def __init__(self, primary: BaseProvider, shadow: BaseProvider, sample_rate: float = 0.1) -> None:
        super().__init__("shadow", priority=95)
        self._primary = primary
        self._shadow = shadow
        self._sample_rate = sample_rate
        self._comparisons: list = []

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        try:
            from arki_project.utils.titanium.crypto import csprng_float
            _rand_fn = csprng_float
        except ImportError:
            import random as _rnd
            _rand_fn = _rnd.random
        primary_task = asyncio.create_task(self._primary.complete(request))

        shadow_task = None
        if _rand_fn() < self._sample_rate:
            shadow_task = asyncio.create_task(self._shadow.complete(request))

        primary_result = await primary_task

        if shadow_task:
            try:
                shadow_result = await asyncio.wait_for(shadow_task, timeout=30)
                self._comparisons.append({
                    "primary": {"provider": self._primary.name, "latency": primary_result.latency},
                    "shadow": {"provider": self._shadow.name, "latency": shadow_result.latency},
                    "timestamp": time.time(),
                })
            except Exception as e:
                logger.debug("Shadow comparison failed: %s", e)

        return primary_result

    @property
    def comparison_stats(self) -> dict:
        if not self._comparisons:
            return {}
        return {
            "total_comparisons": len(self._comparisons),
            "primary_avg_latency": sum(c["primary"]["latency"] for c in self._comparisons[-100:]) / min(len(self._comparisons), 100),
            "shadow_avg_latency": sum(c["shadow"]["latency"] for c in self._comparisons[-100:]) / min(len(self._comparisons), 100),
        }


