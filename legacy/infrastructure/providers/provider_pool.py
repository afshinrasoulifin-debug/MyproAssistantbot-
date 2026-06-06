
from __future__ import annotations
"""
ProviderPool — Connection pool for AI providers with health tracking.
"""
import asyncio, logging, time
try:
    from arki_project.utils.titanium.compat import secure_random as random
except ImportError:
    import random
from typing import Any, Dict, List, Optional
from arki_project.infrastructure.providers.base import (
    BaseProvider, ProviderRequest, ProviderResponse, ProviderStatus
)



logger = logging.getLogger(__name__)

class ProviderPool:
    """Pool of AI providers with weighted selection and auto-healing."""

    def __init__(self, max_concurrent: int = 50) -> None:
        self._providers: Dict[str, BaseProvider] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._health_task: Optional[asyncio.Task] = None
        self._round_robin_idx = 0

    def add(self, provider: BaseProvider) -> None:
        self._providers[provider.name] = provider
        logger.info("Pool: added provider %s (priority=%d)", provider.name, provider.priority)

    def remove(self, name: str) -> None:
        self._providers.pop(name, None)

    @property
    def healthy_providers(self) -> List[BaseProvider]:
        return sorted(
            [p for p in self._providers.values() if p.is_available],
            key=lambda p: (-p.priority, p.metrics.avg_latency)
        )

    async def acquire(self, strategy: str = "best") -> Optional[BaseProvider]:
        """Get a provider from the pool."""
        healthy = self.healthy_providers
        if not healthy:
            return None
        if strategy == "best":
            return healthy[0]
        elif strategy == "round_robin":
            self._round_robin_idx = (self._round_robin_idx + 1) % len(healthy)
            return healthy[self._round_robin_idx]
        elif strategy == "random":
            return random.choice(healthy)
        elif strategy == "least_loaded":
            return min(healthy, key=lambda p: p.metrics.total_requests - p.metrics.successful)
        return healthy[0]

    async def execute(self, request: ProviderRequest, strategy: str = "best") -> ProviderResponse:
        """Execute request through pool with semaphore control."""
        async with self._semaphore:
            provider = await self.acquire(strategy)
            if not provider:
                return ProviderResponse(success=False, error="No healthy providers")
            t0 = time.time()
            try:
                resp = await provider.complete(request)
                provider.metrics.successful += 1
                provider.metrics.total_latency += time.time() - t0
                return resp
            except Exception as e:
                provider.metrics.failed += 1
                provider.metrics.last_error = str(e)
                return ProviderResponse(success=False, error=str(e), provider=provider.name)
            finally:
                provider.metrics.total_requests += 1
                provider.metrics.last_request = time.time()

    async def start_health_monitor(self, interval: float = 30.0) -> None:
        async def _monitor() -> Any:
            while True:
                for p in self._providers.values():
                    try:
                        p.metrics.status = await p.health_check()
                    except Exception:
                        p.metrics.status = ProviderStatus.UNAVAILABLE
                await asyncio.sleep(interval)
        self._health_task = asyncio.create_task(_monitor())

    def stats(self) -> Dict[str, Any]:
        return {
            name: {
                "status": p.metrics.status.name,
                "requests": p.metrics.total_requests,
                "success_rate": f"{p.metrics.success_rate:.1%}",
                "avg_latency": f"{p.metrics.avg_latency:.3f}s",
            }
            for name, p in self._providers.items()
        }


