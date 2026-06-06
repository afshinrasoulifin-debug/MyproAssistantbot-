
from __future__ import annotations
"""
tests/test_market_professor.py — Market Professor Engine Tests
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from datetime import datetime, timezone

@pytest.fixture
def professor():
    from utils.market_professor_engine import MarketProfessorEngine
    return MarketProfessorEngine()

class TestSocialStrategy:
    @pytest.mark.asyncio
    async def test_instagram(self, professor):
        s = await professor.get_social_strategy("instagram")
        assert s["platform"] == "instagram"
        assert "posting_frequency" in s
        assert "content_mix" in s

    @pytest.mark.asyncio
    async def test_pinterest(self, professor):
        s = await professor.get_social_strategy("pinterest")
        assert "board_strategy" in s

    @pytest.mark.asyncio
    async def test_tiktok(self, professor):
        s = await professor.get_social_strategy("tiktok")
        assert "content_ideas" in s

    @pytest.mark.asyncio
    async def test_unknown(self, professor):
        s = await professor.get_social_strategy("myspace")
        assert "error" in s

    def test_content_mix_100(self):
        from utils.market_professor_engine import SOCIAL_STRATEGIES
        assert sum(SOCIAL_STRATEGIES["instagram"]["content_mix"].values()) == 100

class TestMarketAnalysis:
    @pytest.mark.asyncio
    async def test_overview(self, professor):
        r = await professor.analyze_market(dimension="overview")
        assert "overview" in r

    @pytest.mark.asyncio
    async def test_pricing(self, professor):
        r = await professor.analyze_market(dimension="pricing")
        assert r["pricing"]["our_range_eur"]["min"] == 10
        assert r["pricing"]["our_range_eur"]["max"] == 50

    @pytest.mark.asyncio
    async def test_seasonal(self, professor):
        r = await professor.analyze_market(dimension="seasonal")
        assert r["seasonal"]["current_month"] in range(1, 13)

    @pytest.mark.asyncio
    async def test_all(self, professor):
        r = await professor.analyze_market(dimension="all")
        assert "overview" in r and "pricing" in r and "seasonal" in r

class TestSeasonalInsights:
    def test_holiday_oct(self, professor):
        insights = professor._get_seasonal_insights(datetime(2025, 10, 15, tzinfo=timezone.utc))
        assert len(insights) > 0

    def test_xmas_prep_aug(self, professor):
        insights = professor._get_seasonal_insights(datetime(2025, 8, 15, tzinfo=timezone.utc))
        assert any("Christmas" in i.title for i in insights)

    def test_all_months_have_advice(self, professor):
        for m in range(1, 13):
            advice = professor._get_seasonal_advice(m)
            assert len(advice) > 10

    def test_action_items_in_insights(self, professor):
        insights = professor._get_seasonal_insights(datetime(2025, 11, 1, tzinfo=timezone.utc))
        for i in insights:
            assert len(i.action_items) > 0

class TestCompetitorDetection:
    def test_detects_candle(self):
        from utils.market_professor_engine import MarketProfessorEngine
        assert MarketProfessorEngine._is_competitor_brand("Nordic Concrete Candles", "https://x.com", "handmade candle holders")

    def test_skips_diy(self):
        from utils.market_professor_engine import MarketProfessorEngine
        assert not MarketProfessorEngine._is_competitor_brand("How to Make Candles", "https://youtube.com", "DIY tutorial")

class TestBriefing:
    @pytest.mark.asyncio
    async def test_structure(self, professor):
        b = await professor.generate_daily_briefing()
        assert b.date is not None
        assert isinstance(b.insights, list)

    @pytest.mark.asyncio
    async def test_to_dict(self, professor):
        b = await professor.generate_daily_briefing()
        d = b.to_dict()
        assert "date" in d and "insights" in d

    def test_template_summary(self, professor):
        from utils.market_professor_engine import DailyBriefing
        b = DailyBriefing(date="2025-06-01", metrics={"prospects": {"hot": 5, "warm": 10}})
        s = professor._generate_template_summary(b)
        assert "15" in s

    def test_recs_from_leads(self, professor):
        from utils.market_professor_engine import DailyBriefing
        b = DailyBriefing(leads=[{"id": 1}], opportunities=[{"id": 2}])
        recs = professor._generate_recommendations(b)
        assert len(recs) > 0

class TestStats:
    def test_stats(self, professor):
        s = professor.get_stats()
        assert "instagram" in s["social_strategies"]

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


