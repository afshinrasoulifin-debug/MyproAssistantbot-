
"""
tests/test_campaign_orchestrator.py — Campaign Orchestrator Tests
"""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.campaign_orchestrator import (
    CampaignOrchestrator, Campaign, CampaignStep, CampaignAnalytics,
    Lead,
    CampaignType, CampaignStatus, LeadStage, StepType, ChannelType,
    _b2b_outreach_steps, _b2c_social_steps, _competitor_intel_steps,
    _full_funnel_steps, _MarketingHub, _StepExecutor,
)


def _make_offline_orchestrator() -> CampaignOrchestrator:
    """Create orchestrator with all modules disabled (no network calls)."""
    orch = CampaignOrchestrator()
    # Replace hub with one that returns None for everything
    hub = _MarketingHub()
    hub._cache = {k: None for k in [
        "b2b_hunter", "outreach", "platform_intel", "professor",
        "scoring", "deep_recon", "contact_intel", "social_intel",
        "content_forge", "competitor_radar", "campaign_manager", "data_bridge",
    ]}
    hub._available = {k: False for k in hub._cache}
    orch._hub = hub
    orch._executor = _StepExecutor(hub)
    return orch


# ═══════ Data Structures ═══════

class TestDataStructures:
    def test_lead_to_dict(self):
        lead = Lead(company_name="TestCo", domain="test.fi",
                    stage=LeadStage.ENRICHED, score=75.0)
        d = lead.to_dict()
        assert d["company_name"] == "TestCo"
        assert d["stage"] == "enriched"
        assert d["score"] == 75.0

    def test_campaign_step_to_dict(self):
        step = CampaignStep(1, StepType.DISCOVER, config={"max": 50})
        d = step.to_dict()
        assert d["step_number"] == 1
        assert d["step_type"] == "discover"

    def test_campaign_to_dict(self):
        c = Campaign(name="Test", campaign_type=CampaignType.B2B_OUTREACH)
        d = c.to_dict()
        assert d["name"] == "Test"
        assert d["type"] == "b2b_outreach"
        assert d["status"] == "draft"

    def test_analytics_to_dict(self):
        a = CampaignAnalytics(campaign_id="x", total_leads=50,
                               conversion_rate=12.5, avg_score=65.3)
        d = a.to_dict()
        assert d["total_leads"] == 50
        assert d["conversion_rate"] == 12.5

    def test_lead_stages(self):
        assert LeadStage.DISCOVERED.value == "discovered"
        assert LeadStage.CONVERTED.value == "converted"

    def test_campaign_types(self):
        assert CampaignType.B2B_OUTREACH.value == "b2b_outreach"
        assert CampaignType.FULL_FUNNEL.value == "full_funnel"

    def test_channel_types(self):
        assert ChannelType.EMAIL.value == "email"
        assert ChannelType.INSTAGRAM.value == "instagram"

    def test_lead_default_id(self):
        l1 = Lead()
        l2 = Lead()
        assert l1.id != l2.id
        assert len(l1.id) == 12

    def test_campaign_default_id(self):
        c = Campaign()
        assert len(c.id) == 12


# ═══════ Templates ═══════

class TestTemplates:
    def test_b2b_outreach_steps(self):
        steps = _b2b_outreach_steps()
        assert len(steps) >= 8
        types = [s.step_type for s in steps]
        assert StepType.DISCOVER in types
        assert StepType.EMAIL in types

    def test_b2c_social_steps(self):
        steps = _b2c_social_steps()
        assert len(steps) >= 4
        types = [s.step_type for s in steps]
        assert StepType.SOCIAL_POST in types

    def test_competitor_intel_steps(self):
        steps = _competitor_intel_steps()
        types = [s.step_type for s in steps]
        assert StepType.COMPETITOR_SCAN in types

    def test_full_funnel_steps(self):
        steps = _full_funnel_steps()
        assert len(steps) >= 10
        types = [s.step_type for s in steps]
        assert StepType.DISCOVER in types
        assert StepType.EMAIL in types
        assert StepType.SOCIAL_POST in types

    def test_b2b_has_filter(self):
        steps = _b2b_outreach_steps()
        assert any(s.step_type == StepType.FILTER for s in steps)

    def test_b2b_has_wait(self):
        steps = _b2b_outreach_steps()
        assert any(s.step_type == StepType.WAIT for s in steps)


# ═══════ Module Hub ═══════

class TestModuleHub:
    def test_get_status(self):
        hub = _MarketingHub()
        status = hub.get_status()
        assert isinstance(status, dict)
        assert len(status) == 12

    def test_offline_hub(self):
        orch = _make_offline_orchestrator()
        status = orch.get_module_status()
        assert all(v is False for v in status.values())


# ═══════ Campaign Management ═══════

class TestCampaignManagement:
    def test_create_campaign(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("Test B2B", CampaignType.B2B_OUTREACH)
        assert c.name == "Test B2B"
        assert c.status_code == CampaignStatus.DRAFT
        assert len(c.steps) > 0

    def test_create_with_custom_steps(self):
        orch = _make_offline_orchestrator()
        steps = [CampaignStep(1, StepType.DISCOVER), CampaignStep(2, StepType.ANALYZE)]
        c = orch.create_campaign("Custom", custom_steps=steps)
        assert len(c.steps) == 2

    def test_create_with_regions(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("EU", regions=["Finland", "Sweden"],
                                  industries=["hotel", "spa"])
        assert "Finland" in c.target_regions
        assert "hotel" in c.target_industries

    def test_create_with_channels(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("CH", channels=[ChannelType.INSTAGRAM, ChannelType.EMAIL])
        assert ChannelType.INSTAGRAM in c.channels

    def test_create_with_budget(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("Budget", budget=500.0)
        assert c.budget == 500.0

    def test_get_campaign(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("X")
        assert orch.get_campaign(c.id) is c

    def test_get_campaign_not_found(self):
        orch = _make_offline_orchestrator()
        assert orch.get_campaign("nonexistent") is None

    def test_list_campaigns(self):
        orch = _make_offline_orchestrator()
        orch.create_campaign("A")
        orch.create_campaign("B")
        campaigns = orch.list_campaigns()
        assert len(campaigns) == 2

    def test_list_campaigns_by_status(self):
        orch = _make_offline_orchestrator()
        c1 = orch.create_campaign("A")
        c2 = orch.create_campaign("B")
        c1.status_code = CampaignStatus.ACTIVE
        active = orch.list_campaigns(status=CampaignStatus.ACTIVE)
        assert len(active) == 1

    def test_delete_campaign(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("Delete Me")
        assert orch.delete_campaign(c.id) is True
        assert orch.get_campaign(c.id) is None

    def test_delete_nonexistent(self):
        orch = _make_offline_orchestrator()
        assert orch.delete_campaign("nope") is False

    def test_gdpr_flag(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("GDPR", gdpr_compliant=True)
        assert c.gdpr_compliant is True


# ═══════ Lead Management ═══════

class TestLeadManagement:
    def test_add_leads(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("X")
        count = orch.add_leads(c.id, [
            {"company_name": "Hotel A", "domain": "a.fi", "region": "Finland"},
            {"company_name": "Hotel B", "domain": "b.fi"},
        ])
        assert count == 2
        assert len(c.leads) == 2

    def test_add_leads_invalid_campaign(self):
        orch = _make_offline_orchestrator()
        assert orch.add_leads("nope", [{"company_name": "X"}]) == 0

    def test_get_leads(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("X")
        orch.add_leads(c.id, [{"company_name": "A"}, {"company_name": "B"}])
        leads = orch.get_leads(c.id)
        assert len(leads) == 2

    def test_get_leads_by_stage(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("X")
        orch.add_leads(c.id, [{"company_name": "A"}, {"company_name": "B"}])
        c.leads[0].stage = LeadStage.ENRICHED
        leads = orch.get_leads(c.id, stage=LeadStage.ENRICHED)
        assert len(leads) == 1

    def test_get_leads_by_score(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("X")
        orch.add_leads(c.id, [{"company_name": "A"}, {"company_name": "B"}])
        c.leads[0].score = 80.0
        c.leads[1].score = 20.0
        leads = orch.get_leads(c.id, min_score=50.0)
        assert len(leads) == 1

    def test_update_lead_stage(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("X")
        orch.add_leads(c.id, [{"company_name": "A"}])
        lead_id = c.leads[0].id
        assert orch.update_lead_stage(c.id, lead_id, LeadStage.QUALIFIED) is True
        assert c.leads[0].stage == LeadStage.QUALIFIED

    def test_update_lead_stage_not_found(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("X")
        assert orch.update_lead_stage(c.id, "nope", LeadStage.QUALIFIED) is False

    def test_get_leads_invalid_campaign(self):
        orch = _make_offline_orchestrator()
        assert orch.get_leads("nope") == []

    def test_update_stage_invalid_campaign(self):
        orch = _make_offline_orchestrator()
        assert orch.update_lead_stage("nope", "x", LeadStage.LOST) is False


# ═══════ Campaign Execution (offline) ═══════

class TestCampaignExecution:
    @pytest.mark.asyncio
    async def test_run_b2b_campaign(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("B2B Test", CampaignType.B2B_OUTREACH,
                                  regions=["Finland"], industries=["hotel"])
        result = await orch.run_campaign(c.id)
        assert result["status"] == "completed"
        assert result["steps_executed"] > 0
        assert c.status_code == CampaignStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_b2c_campaign(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("Social", CampaignType.B2C_SOCIAL)
        result = await orch.run_campaign(c.id)
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_run_competitor_campaign(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("Intel", CampaignType.COMPETITOR_INTEL)
        result = await orch.run_campaign(c.id)
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_run_full_funnel(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("Full", CampaignType.FULL_FUNNEL)
        result = await orch.run_campaign(c.id)
        assert result["status"] == "completed"
        assert result["steps_executed"] >= 10

    @pytest.mark.asyncio
    async def test_run_not_found(self):
        orch = _make_offline_orchestrator()
        result = await orch.run_campaign("nope")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_run_step(self):
        orch = _make_offline_orchestrator()
        steps = [CampaignStep(1, StepType.WAIT, delay_hours=1)]
        c = orch.create_campaign("Step Test", custom_steps=steps)
        result = await orch.run_step(c.id, 1)
        assert "result" in result
        assert result["result"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_run_step_not_found(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("X")
        result = await orch.run_step(c.id, 999)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_run_step_campaign_not_found(self):
        orch = _make_offline_orchestrator()
        result = await orch.run_step("nope", 1)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_all_steps_marked_complete(self):
        orch = _make_offline_orchestrator()
        steps = [
            CampaignStep(1, StepType.WAIT, delay_hours=0),
            CampaignStep(2, StepType.ANALYZE),
        ]
        c = orch.create_campaign("X", custom_steps=steps)
        await orch.run_campaign(c.id)
        assert all(s.completed for s in c.steps)

    @pytest.mark.asyncio
    async def test_campaign_started_at(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("Time")
        await orch.run_campaign(c.id)
        assert c.started_at is not None
        assert c.completed_at is not None
        assert c.completed_at >= c.started_at


# ═══════ Step Executor ═══════

class TestStepExecutor:
    @pytest.mark.asyncio
    async def test_filter_by_score(self):
        hub = _MarketingHub()
        hub._cache = {k: None for k in ["b2b_hunter","outreach","platform_intel","professor","scoring","deep_recon","contact_intel","social_intel","content_forge","competitor_radar","campaign_manager","data_bridge"]}
        hub._available = {k: False for k in hub._cache}
        executor = _StepExecutor(hub)
        step = CampaignStep(1, StepType.FILTER, condition="score >= 50")
        campaign = Campaign(name="X")
        leads = [
            Lead(company_name="A", score=80.0),
            Lead(company_name="B", score=30.0),
            Lead(company_name="C", score=50.0),
        ]
        result_leads, info = await executor.execute_step(step, campaign, leads)
        assert len(result_leads) == 2
        assert info["filtered_out"] == 1

    @pytest.mark.asyncio
    async def test_filter_by_stage(self):
        hub = _MarketingHub()
        hub._cache = {k: None for k in ["b2b_hunter","outreach","platform_intel","professor","scoring","deep_recon","contact_intel","social_intel","content_forge","competitor_radar","campaign_manager","data_bridge"]}
        hub._available = {k: False for k in hub._cache}
        executor = _StepExecutor(hub)
        step = CampaignStep(1, StepType.FILTER, condition="stage != responded")
        campaign = Campaign(name="X")
        leads = [
            Lead(company_name="A", stage=LeadStage.CONTACTED),
            Lead(company_name="B", stage=LeadStage.RESPONDED),
        ]
        result_leads, info = await executor.execute_step(step, campaign, leads)
        assert len(result_leads) == 1
        assert result_leads[0].company_name == "A"

    @pytest.mark.asyncio
    async def test_wait_step(self):
        hub = _MarketingHub()
        hub._cache = {k: None for k in ["b2b_hunter","outreach","platform_intel","professor","scoring","deep_recon","contact_intel","social_intel","content_forge","competitor_radar","campaign_manager","data_bridge"]}
        hub._available = {k: False for k in hub._cache}
        executor = _StepExecutor(hub)
        step = CampaignStep(1, StepType.WAIT, delay_hours=24)
        campaign = Campaign(name="X")
        leads, info = await executor.execute_step(step, campaign, [])
        assert info["status"] == "completed"
        assert info["wait_hours"] == 24

    @pytest.mark.asyncio
    async def test_analyze_step(self):
        hub = _MarketingHub()
        hub._cache = {k: None for k in ["b2b_hunter","outreach","platform_intel","professor","scoring","deep_recon","contact_intel","social_intel","content_forge","competitor_radar","campaign_manager","data_bridge"]}
        hub._available = {k: False for k in hub._cache}
        executor = _StepExecutor(hub)
        step = CampaignStep(1, StepType.ANALYZE)
        campaign = Campaign(name="X")
        leads = [Lead(score=70.0), Lead(score=50.0)]
        _, info = await executor.execute_step(step, campaign, leads)
        assert info["total_leads"] == 2
        assert info["avg_score"] == 60.0

    @pytest.mark.asyncio
    async def test_discover_offline(self):
        hub = _MarketingHub()
        hub._cache = {k: None for k in ["b2b_hunter","outreach","platform_intel","professor","scoring","deep_recon","contact_intel","social_intel","content_forge","competitor_radar","campaign_manager","data_bridge"]}
        hub._available = {k: False for k in hub._cache}
        executor = _StepExecutor(hub)
        step = CampaignStep(1, StepType.DISCOVER, config={"max_prospects": 5})
        campaign = Campaign(name="X", target_regions=["Finland"], target_industries=["hotel"])
        leads, info = await executor.execute_step(step, campaign, [])
        assert info["discovered"] >= 1

    @pytest.mark.asyncio
    async def test_score_offline(self):
        hub = _MarketingHub()
        hub._cache = {k: None for k in ["b2b_hunter","outreach","platform_intel","professor","scoring","deep_recon","contact_intel","social_intel","content_forge","competitor_radar","campaign_manager","data_bridge"]}
        hub._available = {k: False for k in hub._cache}
        executor = _StepExecutor(hub)
        step = CampaignStep(1, StepType.SCORE)
        campaign = Campaign(name="X")
        leads = [Lead(company_name="A", contact_email="a@a.fi")]
        result_leads, info = await executor.execute_step(step, campaign, leads)
        assert info["scored"] == 1
        assert result_leads[0].score == 50.0  # fallback with email

    @pytest.mark.asyncio
    async def test_content_offline(self):
        hub = _MarketingHub()
        hub._cache = {k: None for k in ["b2b_hunter","outreach","platform_intel","professor","scoring","deep_recon","contact_intel","social_intel","content_forge","competitor_radar","campaign_manager","data_bridge"]}
        hub._available = {k: False for k in hub._cache}
        executor = _StepExecutor(hub)
        step = CampaignStep(1, StepType.CONTENT, config={"calendar_weeks": 2})
        campaign = Campaign(name="X")
        _, info = await executor.execute_step(step, campaign, [])
        assert info["content_pieces"] == 6  # 2 weeks × 3/week


# ═══════ Analytics ═══════

class TestAnalytics:
    @pytest.mark.asyncio
    async def test_get_analytics(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("Analytics Test", CampaignType.B2B_OUTREACH)
        await orch.run_campaign(c.id)
        analytics = orch.get_analytics(c.id)
        assert isinstance(analytics, CampaignAnalytics)
        d = analytics.to_dict()
        assert "total_leads" in d

    def test_get_analytics_no_campaign(self):
        orch = _make_offline_orchestrator()
        a = orch.get_analytics("nope")
        assert a.total_leads == 0

    @pytest.mark.asyncio
    async def test_funnel_report(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("Funnel Test")
        orch.add_leads(c.id, [{"company_name": "A"}, {"company_name": "B"}])
        report = orch.get_funnel_report(c.id)
        assert "funnel" in report
        assert report["total_leads"] == 2

    def test_funnel_report_not_found(self):
        orch = _make_offline_orchestrator()
        result = orch.get_funnel_report("nope")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_analytics_recommendations(self):
        orch = _make_offline_orchestrator()
        c = orch.create_campaign("Recs", CampaignType.B2B_OUTREACH)
        # Small pool = should get recommendation
        orch.add_leads(c.id, [{"company_name": "A"}])
        analytics = orch.get_analytics(c.id)
        assert any("small" in r.lower() or "expand" in r.lower() for r in analytics.recommendations)


# ═══════ Quick Launchers ═══════

class TestQuickLaunchers:
    @pytest.mark.asyncio
    async def test_quick_b2b(self):
        orch = _make_offline_orchestrator()
        result = await orch.quick_b2b("Quick B2B", regions=["Finland"])
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_quick_social(self):
        orch = _make_offline_orchestrator()
        result = await orch.quick_social("Quick Social")
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_quick_competitor_scan(self):
        orch = _make_offline_orchestrator()
        result = await orch.quick_competitor_scan()
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_quick_full_funnel(self):
        orch = _make_offline_orchestrator()
        result = await orch.quick_full_funnel(regions=["Finland"])
        assert result["status"] == "completed"


# ═══════ Stats & Module Status ═══════

class TestStatsAndStatus:
    def test_get_stats(self):
        orch = _make_offline_orchestrator()
        stats = orch.get_stats()
        assert stats["campaigns_created"] == 0
        assert stats["modules_total"] == 12

    @pytest.mark.asyncio
    async def test_stats_after_campaign(self):
        orch = _make_offline_orchestrator()
        await orch.quick_b2b()
        stats = orch.get_stats()
        assert stats["campaigns_created"] >= 1
        assert stats["campaigns_completed"] >= 1

    def test_module_status(self):
        orch = _make_offline_orchestrator()
        status = orch.get_module_status()
        assert isinstance(status, dict)
        assert len(status) == 12


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


