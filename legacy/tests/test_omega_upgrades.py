
"""
tests/test_omega_upgrades.py — OMEGA Engine Upgrade Tests
Tests for the 6 upgraded existing engines.
"""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ═══════ 1. B2BHunterEngine OMEGA ═══════
from utils.b2b_hunter_engine import B2BHunterEngine

class TestB2BHunterOmega:
    def test_has_omega_attrs(self):
        e = B2BHunterEngine()
        assert hasattr(e, '_deep_recon')
        assert hasattr(e, '_contact_intel')

    @pytest.mark.asyncio
    async def test_hunt(self):
        e = B2BHunterEngine(cooldown_hours=0)
        r = await e.hunt("TestRegion", {"id": "test", "search_terms": ["test"]})
        assert r.region == "TestRegion"

# ═══════ 2. OutreachEngine OMEGA ═══════
from utils.outreach_engine import OutreachEngine

class TestOutreachOmega:
    def test_has_content_forge(self):
        e = OutreachEngine()
        assert hasattr(e, '_content_forge')

    @pytest.mark.asyncio
    async def test_generate_email(self):
        e = OutreachEngine()
        prospect = {"business_name": "Hotel", "contact_person": "Anna",
                     "business_type": "hotel", "city": "Helsinki", "country": "Finland"}
        step = {"step_number": 1, "subject_hint": "ArkiObjects", "body_template": "intro"}
        email = await e.generate_email(prospect=prospect, step=step, language="en")
        assert email.subject
        assert email.body_html

# ═══════ 3. PlatformIntelligenceEngine OMEGA ═══════
from utils.platform_intelligence_engine import PlatformIntelligenceEngine

class TestPlatformIntelOmega:
    def test_has_omega_engines(self):
        e = PlatformIntelligenceEngine()
        assert hasattr(e, '_social_intel')
        assert hasattr(e, '_competitor_radar')
        assert hasattr(e, '_content_forge')

    def test_stats_include_omega(self):
        s = PlatformIntelligenceEngine().get_stats()
        assert "omega_social_intel" in s
        assert "omega_competitor_radar" in s

    @pytest.mark.asyncio
    async def test_get_social_intel_report(self):
        r = await PlatformIntelligenceEngine().get_social_intel_report()
        assert isinstance(r, dict)

    @pytest.mark.asyncio
    async def test_get_hashtag_strategy(self):
        r = await PlatformIntelligenceEngine().get_hashtag_strategy()
        assert isinstance(r, dict)

    @pytest.mark.asyncio
    async def test_get_influencer_list(self):
        r = await PlatformIntelligenceEngine().get_influencer_list(limit=3)
        assert isinstance(r, list)

    @pytest.mark.asyncio
    async def test_run_competitor_scan(self):
        r = await PlatformIntelligenceEngine().run_competitor_scan()
        assert isinstance(r, dict)

# ═══════ 4. MarketProfessorEngine OMEGA ═══════
from utils.market_professor_engine import MarketProfessorEngine

class TestMarketProfessorOmega:
    def test_has_omega_engines(self):
        e = MarketProfessorEngine()
        assert hasattr(e, '_deep_recon')
        assert hasattr(e, '_social_intel')
        assert hasattr(e, '_competitor_radar')
        assert hasattr(e, '_contact_intel')
        assert hasattr(e, '_content_forge')

    def test_stats_include_omega(self):
        s = MarketProfessorEngine().get_stats()
        assert "omega_deep_recon" in s

    @pytest.mark.asyncio
    async def test_omega_deep_analysis(self):
        r = await MarketProfessorEngine().omega_deep_competitor_analysis("test-xyz.invalid")
        assert r["domain"] == "test-xyz.invalid"

    @pytest.mark.asyncio
    async def test_omega_market_scan(self):
        r = await MarketProfessorEngine().omega_market_scan()
        assert "generated_at" in r

    @pytest.mark.asyncio
    async def test_omega_content_calendar(self):
        r = await MarketProfessorEngine().omega_content_calendar(weeks=1, posts_per_week=2)
        assert isinstance(r, list)

# ═══════ 5. ProspectScoringEngine OMEGA ═══════
from utils.prospect_scoring_engine import ProspectScoringEngine

class TestProspectScoringOmega:
    def test_has_omega_method(self):
        assert hasattr(ProspectScoringEngine(), '_score_omega_intel')

    def test_no_data(self):
        assert ProspectScoringEngine()._score_omega_intel({}) == 0.0

    def test_with_decision_makers(self):
        p = {"extra_data": {"decision_makers": [{"name": "CEO", "role": "ceo"}]}}
        assert ProspectScoringEngine()._score_omega_intel(p) >= 5.0

    def test_with_owner(self):
        p = {"extra_data": {"decision_makers": [{"name": "O", "role": "owner"}]}}
        assert ProspectScoringEngine()._score_omega_intel(p) >= 7.0

    def test_full_data(self):
        p = {"extra_data": {
            "decision_makers": [{"name": "CEO", "role": "ceo"}],
            "tech_stack": {"cms": "WP"},
            "all_emails": ["a@x.fi", "b@x.fi"],
            "domain_intel": {"accepts_mail": True},
            "dns_intel": {"A": "1.2.3.4"},
        }}
        assert ProspectScoringEngine()._score_omega_intel(p) >= 10.0

    def test_max_cap(self):
        p = {"extra_data": {
            "decision_makers": [{"name": "O", "role": "owner"}],
            "tech_stack": {"x": 1}, "all_emails": ["a@x", "b@x"],
            "domain_intel": {"accepts_mail": True},
            "dns_intel": {"A": "1"}, "security_posture": {"s": 80},
        }}
        assert ProspectScoringEngine()._score_omega_intel(p) <= 15.0

    @pytest.mark.asyncio
    async def test_score_includes_omega(self):
        e = ProspectScoringEngine()
        p = {"business_type": "hotel", "country": "Finland", "status": "qualified",
             "extra_data": {"decision_makers": [{"name": "CEO", "role": "ceo"}]}}
        b = await e.score_prospect(p)
        assert b.factors["omega_intel_bonus"] >= 5.0

# ═══════ 6. MarketingMasterAgent OMEGA ═══════
from core.architecture.agent.marketing_agent import MarketingMasterAgent

class TestMarketingAgentOmega:
    def test_status_has_omega(self):
        s = MarketingMasterAgent().get_status()
        assert "omega_modules" in s
        for k in ["deep_recon", "contact_intel", "social_intel", "content_forge", "competitor_radar"]:
            assert k in s["omega_modules"]

    @pytest.mark.asyncio
    async def test_cmd_deep_recon(self):
        r = await MarketingMasterAgent().handle_command("deep_recon", {"domain": "x.invalid"})
        assert isinstance(r, dict)

    @pytest.mark.asyncio
    async def test_cmd_deep_recon_no_domain(self):
        r = await MarketingMasterAgent().handle_command("deep_recon", {})
        assert "error" in r

    @pytest.mark.asyncio
    async def test_cmd_contact_intel(self):
        r = await MarketingMasterAgent().handle_command("contact_intel", {"company": "X", "domain": "x.invalid"})
        assert isinstance(r, dict)

    @pytest.mark.asyncio
    async def test_cmd_social_intel(self):
        r = await MarketingMasterAgent().handle_command("social_intel", {})
        assert isinstance(r, dict)

    @pytest.mark.asyncio
    async def test_cmd_competitor_radar(self):
        r = await MarketingMasterAgent().handle_command("competitor_radar", {})
        assert isinstance(r, dict)

    @pytest.mark.asyncio
    async def test_cmd_hashtag_strategy(self):
        r = await MarketingMasterAgent().handle_command("hashtag_strategy", {})
        assert isinstance(r, dict)

    @pytest.mark.asyncio
    async def test_cmd_influencers(self):
        r = await MarketingMasterAgent().handle_command("influencers", {"limit": 3})
        assert "influencers" in r

    @pytest.mark.asyncio
    async def test_cmd_content_calendar(self):
        r = await MarketingMasterAgent().handle_command("content_calendar", {"weeks": 1})
        assert "calendar" in r

    @pytest.mark.asyncio
    async def test_cmd_content_forge(self):
        r = await MarketingMasterAgent().handle_command("content_forge", {"type": "social_post"})
        assert isinstance(r, dict)

    @pytest.mark.asyncio
    async def test_cmd_unknown(self):
        r = await MarketingMasterAgent().handle_command("totally_unknown_cmd")
        assert "error" in r


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


