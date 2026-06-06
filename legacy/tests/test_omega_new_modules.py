
"""
tests/test_omega_new_modules.py — OMEGA New Module Tests
Tests for the 5 new OMEGA modules.
"""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ═══════ 1. DeepReconEngine ═══════
from utils.deep_recon_engine import (
    DeepReconEngine, DeepReconReport, TechProfile, _extract_emails, _extract_phones, _classify_page,
)

class TestDeepReconEngine:
    def test_init(self):
        e = DeepReconEngine()
        s = e.get_stats()
        assert s["scans_completed"] == 0
        assert s["total_targets"] == 0

    def test_report_to_dict(self):
        r = DeepReconReport(target="https://example.com", domain="example.com", scan_started="2026-01-01")
        d = r.to_dict()
        assert d["domain"] == "example.com"
        assert d["target"] == "https://example.com"
        assert d["errors"] == []

    def test_tech_profile(self):
        t = TechProfile()
        d = t.to_dict()
        assert "cms" in d
        assert "server" in d

    def test_extract_emails(self):
        emails = _extract_emails("info@test.com sales@test.com", "test.com")
        assert "info@test.com" in emails

    def test_extract_phones(self):
        phones = _extract_phones("Call +358 40 1234567")
        assert len(phones) >= 1

    def test_classify_page(self):
        result = _classify_page("/about", "About Us", "We are a company")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_deep_recon_offline(self):
        e = DeepReconEngine()
        r = await e.deep_recon("test-nonexistent-xyz.invalid")
        assert isinstance(r, DeepReconReport)

    @pytest.mark.asyncio
    async def test_quick_profile(self):
        e = DeepReconEngine()
        r = await e.quick_profile("test-nonexistent-xyz.invalid")
        assert isinstance(r, dict)


# ═══════ 2. ContactIntelEngine ═══════
from utils.contact_intel_engine import (
    ContactIntelEngine, ContactIntelReport, DomainIntel, ContactRole, _classify_role, _normalize_name, _generate_email_candidates,
)

class TestContactIntelEngine:
    def test_init(self):
        e = ContactIntelEngine()
        s = e.get_stats()
        assert s["contacts_discovered"] == 0

    def test_report_to_dict(self):
        r = ContactIntelReport(company_name="TestCo", domain="test.com")
        d = r.to_dict()
        assert d["company_name"] == "TestCo"
        assert d["domain"] == "test.com"

    def test_classify_role_ceo(self):
        role, conf = _classify_role("Chief Executive Officer")
        assert role == ContactRole.CEO
        assert conf > 0.5

    def test_classify_role_unknown(self):
        role, conf = _classify_role("random person")
        assert role in (ContactRole.GENERAL, ContactRole.UNKNOWN)

    def test_normalize_name(self):
        first, last = _normalize_name("anna korhonen")
        assert first == "anna"
        assert last == "korhonen"

    def test_generate_email_candidates(self):
        cands = _generate_email_candidates("Anna", "Korhonen", "test.fi")
        assert len(cands) > 0
        emails = [c.email for c in cands]
        assert any("anna" in e for e in emails)

    @pytest.mark.asyncio
    async def test_discover_contacts_offline(self):
        e = ContactIntelEngine()
        r = await e.discover_contacts("TestCo", "test-nonexistent-xyz.invalid")
        assert isinstance(r, ContactIntelReport)

    def test_domain_intel_to_dict(self):
        di = DomainIntel(domain="example.com", mx_records=["mx.example.com"])
        d = di.to_dict()
        assert d["domain"] == "example.com"


# ═══════ 3. SocialIntelEngine ═══════
from utils.social_intel_engine import (
    SocialIntelEngine, SocialIntelReport, Influencer,
    Community, Platform,
    _analyze_sentiment,
)

class TestSocialIntelEngine:
    def test_init(self):
        e = SocialIntelEngine(niche="handmade candles", region="Finland")
        assert e.niche == "handmade candles"
        assert e.region == "Finland"

    def test_report_to_dict(self):
        r = SocialIntelReport(query="test candles")
        d = r.to_dict()
        assert "influencers" in d
        assert "trends" in d

    def test_influencer_to_dict(self):
        i = Influencer(name="Nordic Candle", platform=Platform.INSTAGRAM,
                       handle="@nordiccandle", url="https://ig.com/nordiccandle",
                       followers_estimate=5000, relevance_score=85.0)
        d = i.to_dict()
        assert d["handle"] == "@nordiccandle"
        assert d["followers_estimate"] == 5000

    def test_community_to_dict(self):
        c = Community(name="Test Group", platform=Platform.FACEBOOK,
                      url="https://fb.com/g", member_count=3000)
        d = c.to_dict()
        assert d["name"] == "Test Group"

    def test_analyze_sentiment(self):
        label, score = _analyze_sentiment("This is absolutely wonderful!")
        assert isinstance(score, float)

    def test_hashtag_strategy(self):
        e = SocialIntelEngine()
        strategy = e.get_hashtag_strategy("product_photo")
        assert isinstance(strategy, dict)

    def test_get_current_trends(self):
        e = SocialIntelEngine()
        trends = e.get_current_trends()
        assert isinstance(trends, list)

    @pytest.mark.asyncio
    async def test_full_social_intel(self):
        e = SocialIntelEngine()
        r = await e.full_social_intel()
        assert isinstance(r, SocialIntelReport)

    @pytest.mark.asyncio
    async def test_discover_influencers(self):
        e = SocialIntelEngine()
        r = await e.discover_influencers(limit=3)
        assert isinstance(r, list)

    @pytest.mark.asyncio
    async def test_find_communities(self):
        e = SocialIntelEngine()
        r = await e.find_communities(limit=3)
        assert isinstance(r, list)


# ═══════ 4. ContentForgeEngine ═══════
from utils.content_forge_engine import (
    ContentForgeEngine, ContentPiece, ContentType, ContentLanguage,
    ContentCalendarEntry, BrandVoice,
)

class TestContentForgeEngine:
    def test_init(self):
        e = ContentForgeEngine()
        s = e.get_stats()
        assert s["emails_generated"] == 0
        assert s["social_posts_generated"] == 0

    def test_piece_to_dict(self):
        p = ContentPiece(content_type=ContentType.SOCIAL_POST,
                         language=ContentLanguage.EN, body="test")
        d = p.to_dict()
        assert d["content_type"] == ContentType.SOCIAL_POST.value

    def test_calendar_entry(self):
        entry = ContentCalendarEntry(date="2026-06-01", platform="instagram",
                                     content_type="product_photo", topic="New collection",
                                     language="en")
        d = entry.to_dict()
        assert d["date"] == "2026-06-01"
        assert d["platform"] == "instagram"

    def test_brand_voice(self):
        bv = BrandVoice()
        d = bv.to_dict()
        assert len(d) > 0

    def test_validate_brand_voice(self):
        e = ContentForgeEngine()
        r = e.validate_brand_voice("Handcrafted with care in Finland")
        assert r["valid"] is True

    def test_content_calendar(self):
        e = ContentForgeEngine()
        entries = e.generate_content_calendar(weeks_ahead=2, posts_per_week=2)
        assert isinstance(entries, list)
        assert len(entries) <= 4

    @pytest.mark.asyncio
    async def test_generate_social_post(self):
        e = ContentForgeEngine()
        p = await e.generate_social_post(platform="instagram", language=ContentLanguage.EN)
        assert isinstance(p, ContentPiece)
        assert p.body

    @pytest.mark.asyncio
    async def test_generate_b2b_email(self):
        e = ContentForgeEngine()
        p = await e.generate_b2b_email(
            prospect={"name": "Anna", "company": "Hotel", "domain": "h.fi"},
            language=ContentLanguage.EN, industry="hotel",
        )
        assert isinstance(p, ContentPiece)

    @pytest.mark.asyncio
    async def test_generate_product_description(self):
        e = ContentForgeEngine()
        p = await e.generate_product_description(
            {"name": "Concrete Holder", "material": "concrete", "price": 25},
            platform="etsy",
        )
        assert isinstance(p, ContentPiece)


# ═══════ 5. CompetitorRadarEngine ═══════
from utils.competitor_radar_engine import (
    CompetitorRadarEngine, CompetitorRadarReport,
    CompetitorProfile, PricePoint, SEOPosition,
    CompetitorAlert, MarketLandscape,
    AlertPriority, ChangeType,
    _extract_prices, _generate_swot,
)

class TestCompetitorRadarEngine:
    def test_init(self):
        e = CompetitorRadarEngine(our_brand="ArkiObjects")
        assert e.our_brand == "ArkiObjects"
        assert e.get_stats()["competitors_tracked"] == 0

    def test_report_to_dict(self):
        r = CompetitorRadarReport()
        d = r.to_dict()
        assert d["competitors"] == []

    def test_extract_prices(self):
        prices = _extract_prices("Cost: €24.99 and 39.50€")
        vals = [p[0] for p in prices]
        assert 24.99 in vals
        assert 39.50 in vals

    def test_extract_prices_empty(self):
        assert _extract_prices("No prices here") == []

    def test_generate_swot(self):
        c = CompetitorProfile(name="TestCo", review_avg=4.8, review_count=200, market_position="leader")
        swot = _generate_swot(c, "ArkiObjects")
        assert swot.competitor == "TestCo"
        assert len(swot.strengths) > 0

    def test_add_remove(self):
        e = CompetitorRadarEngine()
        e.add_competitor("X", domain="x.fi")
        assert len(e.list_tracked()) == 1
        e.remove_competitor("X")
        assert len(e.list_tracked()) == 0

    def test_price_trends(self):
        e = CompetitorRadarEngine()
        e._price_history["T"] = [
            PricePoint("P", 20.0, competitor="T"),
            PricePoint("P", 25.0, competitor="T"),
        ]
        t = e.get_price_trends("T")
        assert t["trend"] == "rising"

    def test_alerts_filter(self):
        e = CompetitorRadarEngine()
        e._alerts = [
            CompetitorAlert("A", ChangeType.PRICE_CHANGE, AlertPriority.HIGH, "T", "D", timestamp="t1"),
            CompetitorAlert("B", ChangeType.NEW_PRODUCT, AlertPriority.LOW, "T", "D", timestamp="t2"),
        ]
        assert len(e.get_alerts(priority=AlertPriority.HIGH)) == 1

    @pytest.mark.asyncio
    async def test_full_scan(self):
        e = CompetitorRadarEngine()
        e.add_competitor("T", domain="t.fi")
        r = await e.full_scan()
        assert isinstance(r, CompetitorRadarReport)
        assert r.market_landscape is not None

    def test_market_landscape(self):
        e = CompetitorRadarEngine()
        e.add_competitor("PremiumCo")
        e._tracked["PremiumCo"].price_range = "€50-100"
        l = e.get_market_landscape()
        assert isinstance(l, MarketLandscape)
        assert l.total_competitors == 1

    def test_seo_position(self):
        p = SEOPosition(keyword="test", position=3, previous_position=8)
        d = p.to_dict()
        assert d["position"] == 3

    def test_stats(self):
        e = CompetitorRadarEngine()
        e.add_competitor("X")
        s = e.get_stats()
        assert s["tracked_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


