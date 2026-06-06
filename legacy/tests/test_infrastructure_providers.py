
"""Tests for infrastructure providers."""
import asyncio
from arki_project.infrastructure.providers.base import (
    BaseProvider, ProviderRequest, ProviderResponse
)
from arki_project.infrastructure.providers.provider_pool import ProviderPool
from arki_project.infrastructure.providers.fallback_provider import FallbackProvider
from arki_project.infrastructure.providers.multi_provider import MultiProvider

class MockProvider(BaseProvider):
    def __init__(self, name, response="test", should_fail=False, priority=0):
        super().__init__(name, priority=priority)
        self._response = response
        self._should_fail = should_fail

    async def complete(self, request):
        if self._should_fail:
            return ProviderResponse(success=False, error="fail")
        return ProviderResponse(content=self._response, success=True, provider=self.name)

def test_provider_pool():
    pool = ProviderPool()
    p1 = MockProvider("gemini", priority=10)
    p2 = MockProvider("groq", priority=5)
    pool.add(p1)
    pool.add(p2)
    assert len(pool.healthy_providers) == 2
    assert pool.healthy_providers[0].name == "gemini"  # Higher priority

def test_fallback_provider():
    async def _test():
        fail = MockProvider("fail", should_fail=True)
        success = MockProvider("success", response="ok")
        fb = FallbackProvider([fail, success])
        req = ProviderRequest(messages=[{"role": "user", "content": "test"}])
        resp = await fb.complete(req)
        assert resp.success
        assert resp.content == "ok"
    asyncio.get_event_loop().run_until_complete(_test())

def test_multi_provider():
    mp = MultiProvider()
    mp.add(MockProvider("a"))
    mp.add(MockProvider("b"))
    assert len(mp._providers) == 2


