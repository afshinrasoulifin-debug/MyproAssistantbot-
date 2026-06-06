
"""Tests for infrastructure gateway."""
import asyncio
from arki_project.infrastructure.gateway.ai_gateway import AIGateway, GatewayRequest, GatewayResponse
from arki_project.infrastructure.gateway.smart_gateway import SmartGateway

def test_gateway_creation():
    gw = AIGateway()
    assert gw._request_count == 0

def test_gateway_process():
    async def _test():
        gw = AIGateway()
        async def handler(req):
            return GatewayResponse(content="hello", success=True)
        gw.set_handler(handler)
        req = GatewayRequest(messages=[{"role": "user", "content": "hi"}])
        resp = await gw.process(req)
        assert resp.success
        assert resp.content == "hello"
        assert gw._request_count == 1
    asyncio.get_event_loop().run_until_complete(_test())

def test_smart_gateway():
    gw = SmartGateway()
    assert gw.recommend_model() == "gemini-pro"  # Default


