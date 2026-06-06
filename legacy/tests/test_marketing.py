
"""
tg_bot/tests/test_marketing.py — Marketing Engine Tests
════════════════════════════════════════════════════════
"""

import sys
import os

# Ensure parent on path and register a lightweight arki_project.utils stub
# so marketing_engine can import without pulling in heavy deps
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_parent = os.path.dirname(_root)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

# Stub out utils/__init__.py heavy imports before loading marketing_engine
import types
_fake_utils = types.ModuleType("arki_project.utils")
_fake_utils.__path__ = [os.path.join(_root, "utils")]
_fake_utils.__package__ = "arki_project.utils"
sys.modules.setdefault("arki_project.utils", _fake_utils)

from arki_project.utils.marketing_engine import (
    MarketingEngine, Platform, CampaignPhase, ContentCalendarItem,
)


class TestMarketingEngine:
    """Tests for the Marketing Engine."""

    def setup_method(self):
        self.engine = MarketingEngine()

    def test_create_campaign(self):
        campaign = self.engine.create_campaign(
            user_id=1, name="Summer Sale", platforms=["instagram", "tiktok"]
        )
        assert campaign.campaign_id
        assert campaign.name == "Summer Sale"
        assert campaign.phase == CampaignPhase.PLANNING
        assert len(campaign.platforms) == 2

    def test_advance_campaign_phase(self):
        campaign = self.engine.create_campaign(1, "Test", ["instagram"])
        new_phase = self.engine.advance_campaign_phase(campaign.campaign_id)
        assert new_phase == CampaignPhase.CONTENT_CREATION

    def test_content_calendar_generation(self):
        calendar = self.engine.generate_content_calendar(
            days=7, platforms=[Platform.INSTAGRAM]
        )
        assert len(calendar) == 7
        assert all(isinstance(item, ContentCalendarItem) for item in calendar)
        assert all(item.platform == Platform.INSTAGRAM for item in calendar)

    def test_content_calendar_multi_platform(self):
        calendar = self.engine.generate_content_calendar(
            days=3, platforms=[Platform.INSTAGRAM, Platform.TIKTOK]
        )
        assert len(calendar) == 6  # 3 days × 2 platforms

    def test_content_calendar_pillar_distribution(self):
        calendar = self.engine.generate_content_calendar(days=100, platforms=[Platform.INSTAGRAM])
        pillar_counts = {}
        for item in calendar:
            pillar_counts[item.pillar] = pillar_counts.get(item.pillar, 0) + 1
        # All pillars should be represented
        assert len(pillar_counts) >= 3

    def test_ab_test_creation(self):
        test_id = self.engine.create_ab_test(1, ["Caption A", "Caption B"])
        assert test_id
        assert test_id in self.engine._ab_tests
        assert len(self.engine._ab_tests[test_id]) == 2

    def test_ab_test_record_and_winner(self):
        test_id = self.engine.create_ab_test(1, ["A wins", "B loses"])
        # Simulate data
        self.engine.record_ab_result(test_id, 0, impressions=200, clicks=40)
        self.engine.record_ab_result(test_id, 1, impressions=200, clicks=20)
        
        result = self.engine.get_ab_winner(test_id)
        assert result["status"] in ("significant", "trending")
        assert result["winner"]["ctr"] > 0

    def test_ab_test_insufficient_data(self):
        test_id = self.engine.create_ab_test(1, ["A", "B"])
        self.engine.record_ab_result(test_id, 0, impressions=10, clicks=2)
        result = self.engine.get_ab_winner(test_id)
        assert result["status"] == "insufficient_data"

    def test_platform_specs(self):
        specs = self.engine.get_platform_specs(Platform.INSTAGRAM)
        assert specs["max_caption_length"] == 2200
        assert specs["max_hashtags"] == 30

    def test_platform_specs_etsy(self):
        specs = self.engine.get_platform_specs(Platform.ETSY)
        assert specs["max_title_length"] == 140
        assert specs["max_tags"] == 13

    def test_adapt_content_cross_platform(self):
        adaptation = self.engine.adapt_content_for_platform(
            "Long Instagram caption here...",
            Platform.INSTAGRAM,
            Platform.TIKTOK,
        )
        assert adaptation["target_platform"] == "tiktok"
        assert "Shorten" in adaptation["length_adjustment"]

    def test_audience_segment_creation(self):
        segment = self.engine.create_segment(
            user_id=1,
            name="Eco-conscious",
            description="Environmentally aware consumers",
            interests=["sustainability", "handmade"],
            demographics={"age": "25-40", "income": "medium-high"},
        )
        assert segment.name == "Eco-conscious"
        segments = self.engine.get_segments(1)
        assert len(segments) == 1

    def test_hashtag_strategy(self):
        strategy = self.engine.generate_hashtag_strategy(
            Platform.INSTAGRAM, "handmade candles", "ArkiShop"
        )
        assert "branded" in strategy
        assert "niche" in strategy
        assert "recommended_mix" in strategy
        assert len(strategy["branded"]) >= 1

    def test_competitor_analysis_prompt(self):
        prompt = self.engine.build_competitor_analysis_prompt(
            "Competitor sells similar handmade items on Etsy",
            {"name": "TestBrand", "style": "Minimalist", "products": "Candles"},
        )
        assert "SWOT" in prompt
        assert "TestBrand" in prompt
        assert "ACTIONABLE" in prompt


