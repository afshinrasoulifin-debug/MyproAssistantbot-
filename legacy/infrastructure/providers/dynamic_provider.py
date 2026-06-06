
from __future__ import annotations
"""
DynamicProvider — Self-tuning provider that adapts based on performance.
"""
import logging, time
try:
    from arki_project.utils.titanium.compat import secure_random as random
except ImportError:
    import random
from typing import Dict, Any
from arki_project.infrastructure.providers.base import BaseProvider, ProviderRequest, ProviderResponse



logger = logging.getLogger(__name__)

class DynamicProvider(BaseProvider):
    """Dynamically adjusts provider weights based on real-time performance."""

    def __init__(self, exploration_rate: float = 0.1) -> None:
        super().__init__("dynamic", priority=85)
        self._providers: Dict[str, BaseProvider] = {}
        self._weights: Dict[str, float] = {}
        self._exploration_rate = exploration_rate

    def add(self, provider: BaseProvider, initial_weight: float = 1.0) -> Any:
        self._providers[provider.name] = provider
        self._weights[provider.name] = initial_weight

    def _select(self) -> BaseProvider:
        available = {k: v for k, v in self._providers.items() if v.is_available}
        if not available:
            raise RuntimeError("No providers")
        if random.random() < self._exploration_rate:
            return random.choice(list(available.values()))
        weights = {k: self._weights.get(k, 1.0) for k in available}
        total = sum(weights.values())
        r = random.uniform(0, total)
        cumulative = 0
        for name, w in weights.items():
            cumulative += w
            if r <= cumulative:
                return available[name]
        return list(available.values())[0]

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        provider = self._select()
        t0 = time.time()
        try:
            resp = await provider.complete(request)
            latency = time.time() - t0
            if resp.success:
                self._weights[provider.name] = min(self._weights.get(provider.name, 1) * 1.05, 10.0)
            else:
                self._weights[provider.name] = max(self._weights.get(provider.name, 1) * 0.8, 0.1)
            return resp
        except Exception as e:
            self._weights[provider.name] = max(self._weights.get(provider.name, 1) * 0.5, 0.1)
            return ProviderResponse(success=False, error=str(e))


