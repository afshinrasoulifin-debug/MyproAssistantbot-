
from __future__ import annotations
"""
tests/test_marketing_agent.py — Marketing Agent TITAN Integration Tests
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

class TestConfig:
    def test_config_loads(self):
        from config_marketing import DEFAULT_BRAND, DEFAULT_TARGET_MARKETS, B2B_CATEGORIES, PLATFORM_REGISTRY
        assert DEFAULT_BRAND["name"] == "ArkiObjects"
        assert len(DEFAULT_TARGET_MARKETS) >= 5
        assert len(B2B_CATEGORIES) >= 4
        assert len(PLATFORM_REGISTRY) >= 10

    def test_brand_fields(self):
        from config_marketing import DEFAULT_BRAND
        for k in ("name", "location", "price_range_eur"):
            assert k in DEFAULT_BRAND

    def test_finland_in_markets(self):
        from config_marketing import DEFAULT_TARGET_MARKETS
        assert any("Finland" in str(m) for m in DEFAULT_TARGET_MARKETS)

    def test_etsy_in_registry(self):
        from config_marketing import PLATFORM_REGISTRY
        assert "etsy" in PLATFORM_REGISTRY

class TestDataBridge:
    def test_singleton(self):
        from utils.marketing_data_bridge import get_data_bridge
        assert get_data_bridge() is get_data_bridge()

    def test_prospect_fingerprint(self):
        from utils.marketing_data_bridge import prospect_fingerprint
        fp1 = prospect_fingerprint("Hotel ABC", "Helsinki", "Finland")
        fp2 = prospect_fingerprint("Hotel ABC", "Helsinki", "Finland")
        fp3 = prospect_fingerprint("Hotel XYZ", "Helsinki", "Finland")
        assert fp1 == fp2 and fp1 != fp3

    def test_fingerprint_case(self):
        from utils.marketing_data_bridge import prospect_fingerprint
        assert prospect_fingerprint("A", "B", "C") == prospect_fingerprint("a", "b", "c")

    def test_opportunity_fingerprint(self):
        from utils.marketing_data_bridge import opportunity_fingerprint
        fp1 = opportunity_fingerprint("Market A", "FI", "2025-12-01")
        fp2 = opportunity_fingerprint("Market A", "FI", "2025-12-01")
        assert fp1 == fp2

class TestAllImports:
    def test_imports(self):
        pass

    def test_engine_creation(self):
        from utils.prospect_scoring_engine import ProspectScoringEngine
        from utils.b2b_hunter_engine import B2BHunterEngine
        from utils.outreach_engine import OutreachEngine
        from utils.platform_intelligence_engine import PlatformIntelligenceEngine
        from utils.market_professor_engine import MarketProfessorEngine
        from utils.marketing_campaign_manager import MarketingCampaignManager
        ProspectScoringEngine(); B2BHunterEngine(); OutreachEngine()
        PlatformIntelligenceEngine(); MarketProfessorEngine(); MarketingCampaignManager()

class TestEventBus:
    @pytest.mark.asyncio
    async def test_pub_sub(self):
        from services.marketing_automation_service import MarketingEventBus
        bus = MarketingEventBus()
        received = []
        async def handler(data): received.append(data)
        bus.subscribe("test", handler)
        await bus.publish("test", {"k": "v"})
        assert len(received) == 1 and received[0]["k"] == "v"

    @pytest.mark.asyncio
    async def test_history(self):
        from services.marketing_automation_service import MarketingEventBus
        bus = MarketingEventBus()
        await bus.publish("a", {"x": 1}); await bus.publish("b", {"y": 2})
        assert len(bus.get_history()) == 2
        assert len(bus.get_history(event_type="a")) == 1

class TestAgentInit:
    def test_creates(self):
        from core.architecture.agent.marketing_agent import MarketingMasterAgent
        a = MarketingMasterAgent(admin_ids={12345})
        assert a.AGENT_NAME == "marketing_master"
        assert a.AGENT_VERSION == "1.0.0-TITAN"

    def test_status(self):
        from core.architecture.agent.marketing_agent import MarketingMasterAgent
        a = MarketingMasterAgent()
        s = a.get_status()
        assert s["initialized"] is False
        assert isinstance(s["engines"], dict)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


