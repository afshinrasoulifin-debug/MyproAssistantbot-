
"""
campaign_orchestrator_pkg/campaign_orchestrator.py — CampaignOrchestrator
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class CampaignOrchestrator:
    """
    Supreme Campaign Orchestrator — unifies all 12 marketing modules
    into automated multi-step campaigns.

    Usage:
        orch = CampaignOrchestrator()
        campaign = orch.create_campaign("Nordic Hotels B2B", CampaignType.B2B_OUTREACH)
        result = await orch.run_campaign(campaign.id)
        analytics = orch.get_analytics(campaign.id)
    """

    def __init__(self):
        self._hub = _MarketingHub()
        self._executor = _StepExecutor(self._hub)
        self._campaigns: Dict[str, Campaign] = {}
        self._stats = {
            "campaigns_created": 0, "campaigns_completed": 0,
            "campaigns_active": 0, "total_leads_processed": 0,
            "total_emails_sent": 0, "total_content_pieces": 0,
        }

    # ─── Campaign Management ──────────────────────────────────

    def create_campaign(
        self,
        name: str,
        campaign_type: CampaignType = CampaignType.B2B_OUTREACH,
        regions: Optional[List[str]] = None,
        industries: Optional[List[str]] = None,
        channels: Optional[List[ChannelType]] = None,
        budget: float = 0.0,
        custom_steps: Optional[List[CampaignStep]] = None,
        gdpr_compliant: bool = True,
    ) -> Campaign:
        """Create a new campaign with template or custom steps."""
        # Get template steps or use custom
        if custom_steps:
            steps = custom_steps
        elif campaign_type in _TEMPLATES:
            steps = _TEMPLATES[campaign_type]()
        else:
            steps = _b2b_outreach_steps()

        campaign = Campaign(
            name=name,
            campaign_type=campaign_type,
            steps=steps,
            target_regions=regions or ["Finland"],
            target_industries=industries or ["hospitality", "retail", "spa"],
            channels=channels or [ChannelType.EMAIL, ChannelType.INSTAGRAM],
            budget=budget,
            gdpr_compliant=gdpr_compliant,
        )

        self._campaigns[campaign.id] = campaign
        self._stats["campaigns_created"] += 1
        return campaign

    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Get campaign by ID."""
        return self._campaigns.get(campaign_id)

    def list_campaigns(
        self,
        status: Optional[CampaignStatus] = None,
    ) -> List[Dict[str, Any]]:
        """List all campaigns, optionally filtered by status."""
        campaigns = self._campaigns.values()
        if status:
            campaigns = [c for c in campaigns if c.status_code == status]
        return [c.to_dict() for c in campaigns]

    def delete_campaign(self, campaign_id: str) -> bool:
        """Delete a campaign."""
        return self._campaigns.pop(campaign_id, None) is not None

    # ─── Campaign Execution ───────────────────────────────────

    async def run_campaign(
        self,
        campaign_id: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Run a campaign through all its steps."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return {"error": f"Campaign {campaign_id} not found"}

        campaign.status_code = CampaignStatus.ACTIVE
        campaign.started_at = time.time()
        self._stats["campaigns_active"] += 1

        leads = list(campaign.leads)
        step_results = []

        for step in campaign.steps:
            if step.completed:
                continue

            # Execute step
            leads, result = await self._executor.execute_step(step, campaign, leads)
            step.completed = True
            step.result = result
            step_results.append({
                "step": step.step_number,
                "type": step.step_type.value,
                "result": result,
            })

            # Update campaign leads
            campaign.leads = leads

        campaign.status_code = CampaignStatus.COMPLETED
        campaign.completed_at = time.time()
        campaign.metrics["step_results"] = step_results
        campaign.metrics["final_lead_count"] = len(leads)

        self._stats["campaigns_completed"] += 1
        self._stats["campaigns_active"] = max(0, self._stats["campaigns_active"] - 1)
        self._stats["total_leads_processed"] += len(leads)

        return {
            "campaign_id": campaign_id,
            "status": "completed",
            "steps_executed": len(step_results),
            "leads_processed": len(leads),
            "step_results": step_results,
        }

    async def run_step(
        self,
        campaign_id: str,
        step_number: int,
    ) -> Dict[str, Any]:
        """Run a specific step of a campaign."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return {"error": f"Campaign {campaign_id} not found"}

        step = next((s for s in campaign.steps if s.step_number == step_number), None)
        if not step:
            return {"error": f"Step {step_number} not found"}

        leads, result = await self._executor.execute_step(step, campaign, campaign.leads)
        step.completed = True
        step.result = result
        campaign.leads = leads

        return {"step": step_number, "result": result}

    # ─── Lead Management ──────────────────────────────────────

    def add_leads(
        self,
        campaign_id: str,
        leads: List[Dict[str, Any]],
    ) -> int:
        """Manually add leads to a campaign."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return 0

        added = 0
        for data in leads:
            lead = Lead(
                company_name=data.get("company_name", ""),
                domain=data.get("domain", ""),
                contact_name=data.get("contact_name", ""),
                contact_email=data.get("contact_email", ""),
                region=data.get("region", ""),
                industry=data.get("industry", ""),
                source="manual",
            )
            campaign.leads.append(lead)
            added += 1
        return added

    def get_leads(
        self,
        campaign_id: str,
        stage: Optional[LeadStage] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Get leads from a campaign with optional filters."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return []

        leads = campaign.leads
        if stage:
            leads = [l for l in leads if l.stage == stage]
        if min_score > 0:
            leads = [l for l in leads if l.score >= min_score]

        return [l.to_dict() for l in leads]

    def update_lead_stage(
        self,
        campaign_id: str,
        lead_id: str,
        new_stage: LeadStage,
    ) -> bool:
        """Update a lead's stage."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return False

        for lead in campaign.leads:
            if lead.id == lead_id:
                lead.stage = new_stage
                lead.updated_at = time.time()
                return True
        return False

    # ─── Analytics ────────────────────────────────────────────

    def get_analytics(self, campaign_id: str) -> CampaignAnalytics:
        """Get comprehensive analytics for a campaign."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return CampaignAnalytics(campaign_id=campaign_id)

        leads = campaign.leads
        stages = {}
        for lead in leads:
            s = lead.stage.value
            stages[s] = stages.get(s, 0) + 1

        total = len(leads)
        emails_sent = sum(
            1 for l in leads
            for i in l.interactions
            if i.get("type") in ("email_sent", "email_queued")
        )
        contacted = stages.get("contacted", 0) + stages.get("responded", 0) + stages.get("qualified", 0)
        converted = stages.get("converted", 0)
        avg_score = sum(l.score for l in leads) / max(total, 1)

        recs = []
        if avg_score < 40:
            recs.append("Average lead score is low — consider tightening discovery criteria")
        if contacted > 0 and converted == 0:
            recs.append("No conversions yet — consider A/B testing email templates")
        if total < 20:
            recs.append("Lead pool is small — expand target regions or industries")

        return CampaignAnalytics(
            campaign_id=campaign_id,
            total_leads=total,
            leads_by_stage=stages,
            conversion_rate=round(converted / max(contacted, 1) * 100, 2),
            avg_score=round(avg_score, 1),
            emails_sent=emails_sent,
            content_pieces=sum(
                r.get("content_pieces", 0) for s in campaign.steps
                if s.result for r in [s.result]
            ),
            recommendations=recs,
        )

    def get_funnel_report(self, campaign_id: str) -> Dict[str, Any]:
        """Get a funnel visualization of lead stages."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return {"error": "Campaign not found"}

        stages_order = [
            LeadStage.DISCOVERED, LeadStage.ENRICHED, LeadStage.SCORED,
            LeadStage.CONTACTED, LeadStage.RESPONDED, LeadStage.QUALIFIED,
            LeadStage.NEGOTIATING, LeadStage.CONVERTED,
        ]
        funnel = []
        for stage in stages_order:
            count = sum(1 for l in campaign.leads if l.stage == stage)
            funnel.append({"stage": stage.value, "count": count})

        return {
            "campaign": campaign.name,
            "funnel": funnel,
            "total_leads": len(campaign.leads),
            "lost": sum(1 for l in campaign.leads if l.stage == LeadStage.LOST),
        }

    # ─── Module Status & Stats ────────────────────────────────

    def get_module_status(self) -> Dict[str, bool]:
        """Get availability of all marketing modules."""
        return self._hub.get_status()

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            **self._stats,
            "modules_available": sum(
                1 for v in self._hub.get_status().values() if v
            ),
            "modules_total": 12,
            "active_campaigns": [
                c.to_dict() for c in self._campaigns.values()
                if c.status_code == CampaignStatus.ACTIVE
            ],
        }

    # ─── Quick Launchers ──────────────────────────────────────

    async def quick_b2b(
        self,
        name: str = "Quick B2B",
        regions: Optional[List[str]] = None,
        industries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Quickly launch a B2B outreach campaign."""
        c = self.create_campaign(
            name, CampaignType.B2B_OUTREACH,
            regions=regions, industries=industries,
        )
        return await self.run_campaign(c.id)

    async def quick_social(
        self,
        name: str = "Quick Social",
        channels: Optional[List[ChannelType]] = None,
    ) -> Dict[str, Any]:
        """Quickly launch a social media campaign."""
        c = self.create_campaign(
            name, CampaignType.B2C_SOCIAL,
            channels=channels or [ChannelType.INSTAGRAM, ChannelType.PINTEREST],
        )
        return await self.run_campaign(c.id)

    async def quick_competitor_scan(
        self,
        name: str = "Competitor Scan",
    ) -> Dict[str, Any]:
        """Quickly run a competitor intel campaign."""
        c = self.create_campaign(name, CampaignType.COMPETITOR_INTEL)
        return await self.run_campaign(c.id)

    async def quick_full_funnel(
        self,
        name: str = "Full Funnel",
        regions: Optional[List[str]] = None,
        industries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Launch a comprehensive full-funnel campaign."""
        c = self.create_campaign(
            name, CampaignType.FULL_FUNNEL,
            regions=regions, industries=industries,
        )
        return await self.run_campaign(c.id)



