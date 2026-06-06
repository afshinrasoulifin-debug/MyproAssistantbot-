
from __future__ import annotations
"""tests/test_platform_intelligence.py — Platform Intelligence Engine Tests"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

@pytest.fixture
def engine():
    from utils.platform_intelligence_engine import PlatformIntelligenceEngine
    from config_marketing import PLATFORM_REGISTRY
    return PlatformIntelligenceEngine(platform_registry=PLATFORM_REGISTRY)

@pytest.fixture
def empty_engine():
    from utils.platform_intelligence_engine import PlatformIntelligenceEngine
    return PlatformIntelligenceEngine()

class TestRegistry:
    def test_loaded(self, engine): assert len(engine._registry) > 0
    def test_etsy(self, engine): assert "etsy" in engine._registry
    def test_has_name(self, engine):
        for k, p in engine._registry.items(): assert "name" in p
    def test_empty(self, empty_engine): assert len(empty_engine._registry) == 0

class TestStats:
    def test_structure(self, engine):
        s = engine.get_stats()
        assert "total_platforms" in s and s["total_platforms"] > 0
    def test_empty(self, empty_engine):
        s = empty_engine.get_stats()
        assert s["total_platforms"] == 0

class TestHelpers:
    def test_is_event(self, engine):
        assert engine._is_potential_event("Christmas Market Helsinki 2025", "craft fair artisans")
    def test_not_event(self, engine):
        assert not engine._is_potential_event("Random Blog Post", "cooking recipes")
    def test_classify(self):
        from utils.platform_intelligence_engine import PlatformIntelligenceEngine
        assert isinstance(PlatformIntelligenceEngine._classify_event("Christmas Market", "craft fair"), str)
    def test_score_relevance(self):
        from utils.platform_intelligence_engine import PlatformIntelligenceEngine
        assert PlatformIntelligenceEngine._score_platform_relevance("Handmade Marketplace", "artisan products") > 0

class TestDiscoveryResult:
    def test_to_dict(self):
        from utils.platform_intelligence_engine import DiscoveryResult
        r = DiscoveryResult(platforms_checked=5, opportunities_new=3, events_found=2)
        d = r.to_dict()
        assert d["platforms_checked"] == 5 and d["opportunities_new"] == 3

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


