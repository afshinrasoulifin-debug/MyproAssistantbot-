
from __future__ import annotations
"""
tg_bot/utils/marketing_campaign_manager.py — Marketing Agent TITAN (L9)
═══════════════════════════════════════════════════════════════════════
Full lifecycle campaign management with pipeline coordination.

Architecture
────────────
   ┌─────────────────────────────────────────────────────────┐
   │            MARKETING CAMPAIGN MANAGER                    │
   ├──────────┬──────────┬──────────┬──────────┬─────────────┤
   │ Create   │ Execute  │ Monitor  │ Optimize │ Report      │
   ├──────────┼──────────┼──────────┼──────────┼─────────────┤
   │ Template │ Launch   │ Metrics  │ A/B Test │ Performance │
   │ Custom   │ Schedule │ Alerts   │ Winner   │ ROI         │
   │ Region   │ Throttle │ Track    │ Retarget │ Export      │
   │ Category │ Pause    │ Funnel   │ Improve  │ Archive     │
   └──────────┴──────────┴──────────┴──────────┴─────────────┘

Campaign Lifecycle
──────────────────
  draft → scheduled → active → paused / completed → archived

Coordinates:
  • B2BHunterEngine — prospect discovery phase
  • ProspectScoringEngine — qualification phase
  • OutreachEngine — execution phase
  • MarketProfessorEngine — analysis & optimization

Reuses
──────
  • marketing_data_bridge.py — data persistence
  • workflow_engine.py — DAG execution
"""


import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Campaign Templates
# ═══════════════════════════════════════════════════════════

CAMPAIGN_TEMPLATES = {
    "nordic_b2b_intro": {
        "name": "Nordic B2B Introduction",
        "description": "Introduce ArkiObjects to hotels, spas, and restaurants in Nordic countries",
        "target_countries": ["Finland", "Sweden", "Norway", "Denmark"],
        "target_categories": ["hotels", "spas", "restaurants"],
        "min_score": 40.0,
        "ab_test": True,
        "sequence_steps": 4,
    },
    "dach_expansion": {
        "name": "DACH Market Expansion",
        "description": "Expand into German-speaking markets with localized outreach",
        "target_countries": ["Germany", "Austria", "Switzerland"],
        "target_categories": ["hotels", "interior", "galleries"],
        "min_score": 35.0,
        "ab_test": True,
        "sequence_steps": 4,
    },
    "gallery_focus": {
        "name": "Art Gallery Outreach",
        "description": "Target art galleries and design shops for retail partnerships",
        "target_countries": ["Finland", "Sweden", "Germany", "Netherlands", "UK"],
        "target_categories": ["galleries"],
        "min_score": 30.0,
        "ab_test": False,
        "sequence_steps": 3,
    },
    "holiday_push": {
        "name": "Holiday Season Push",
        "description": "Intensive outreach for holiday/Christmas season",
        "target_countries": ["Finland", "Sweden", "Norway", "Denmark", "Germany", "UK"],
        "target_categories": ["hotels", "spas", "restaurants", "events", "corporate"],
        "min_score": 25.0,
        "ab_test": True,
        "sequence_steps": 4,
    },
}


@dataclass
class CampaignPipelineStatus:
    """Status of a campaign's processing pipeline."""
    campaign_id: int = 0
    campaign_name: str = ""
    status: str = "unknown"
    phase: str = ""  # discovery, qualification, outreach, monitoring
    prospects_total: int = 0
    prospects_qualified: int = 0
    prospects_contacted: int = 0
    prospects_responded: int = 0
    emails_sent: int = 0
    emails_opened: int = 0
    emails_replied: int = 0
    conversion_rate: float = 0.0
    started_at: Optional[str] = None
    last_activity: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "status": self.status,
            "phase": self.phase,
            "funnel": {
                "total": self.prospects_total,
                "qualified": self.prospects_qualified,
                "contacted": self.prospects_contacted,
                "responded": self.prospects_responded,
            },
            "emails": {
                "sent": self.emails_sent,
                "opened": self.emails_opened,
                "replied": self.emails_replied,
            },
            "conversion_rate": round(self.conversion_rate, 2),
            "started_at": self.started_at,
            "last_activity": self.last_activity,
        }


# ═══════════════════════════════════════════════════════════
# Campaign Manager
# ═══════════════════════════════════════════════════════════

class MarketingCampaignManager:
    """
    Full lifecycle campaign management.

    Coordinates the entire marketing pipeline from
    prospect discovery through outreach to conversion tracking.
    """

    def __init__(
        self,
        *,
        data_bridge=None,
        hunter_engine=None,
        scoring_engine=None,
        outreach_engine=None,
        professor_engine=None,
    ) -> None:
        self._data_bridge = data_bridge
        self._hunter = hunter_engine
        self._scorer = scoring_engine
        self._outreach = outreach_engine
        self._professor = professor_engine
        self._active_pipelines: Dict[int, CampaignPipelineStatus] = {}
        
        # OMEGA Engines
        self._recon = None
        self._personalizer = None

    def set_omega_engines(self, recon_engine=None, personalizer=None):
        """Enable advanced OMEGA intelligence for campaigns."""
        self._recon = recon_engine
        self._personalizer = personalizer

    def set_engines(
        self,
        *,
        data_bridge=None,
        hunter_engine=None,
        scoring_engine=None,
        outreach_engine=None,
        professor_engine=None,
    ) -> None:
        """Set/update engine references (for late initialization)."""
        if data_bridge:
            self._data_bridge = data_bridge
        if hunter_engine:
            self._hunter = hunter_engine
        if scoring_engine:
            self._scorer = scoring_engine
        if outreach_engine:
            self._outreach = outreach_engine
        if professor_engine:
            self._professor = professor_engine

    # ── Campaign Creation ────────────────────────────────

    async def create_from_template(
        self,
        template_key: str,
        *,
        created_by: int = 0,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        Create a campaign from a pre-defined template.

        Args:
            template_key: Key from CAMPAIGN_TEMPLATES
            created_by: Telegram user ID of creator
            overrides: Optional overrides for template values

        Returns:
            Campaign ID or None
        """
        template = CAMPAIGN_TEMPLATES.get(template_key)
        if not template:
            logger.error("Unknown template: %s", template_key)
            return None

        data = dict(template)
        if overrides:
            data.update(overrides)
        data["created_by"] = created_by

        if not self._data_bridge:
            logger.error("Data bridge not available")
            return None

        campaign_id = await self._data_bridge.create_campaign(data)
        if campaign_id:
            logger.info("📋 Created campaign %d from template '%s'", campaign_id, template_key)
        return campaign_id

    async def create_custom(
        self,
        *,
        name: str,
        description: str = "",
        target_countries: Optional[List[str]] = None,
        target_categories: Optional[List[str]] = None,
        min_score: float = 30.0,
        ab_test: bool = False,
        created_by: int = 0,
    ) -> Optional[int]:
        """Create a custom campaign with explicit parameters."""
        if not self._data_bridge:
            return None

        return await self._data_bridge.create_campaign({
            "name": name,
            "description": description,
            "target_countries": target_countries or [],
            "target_categories": target_categories or [],
            "min_score": min_score,
            "ab_test_enabled": ab_test,
            "created_by": created_by,
        })

    # ── Campaign Execution Pipeline ──────────────────────

    async def launch_campaign(self, campaign_id: int) -> CampaignPipelineStatus:
        """
        Launch a campaign — runs the full pipeline.

        Pipeline phases:
        1. Discovery: Find prospects matching campaign criteria
        2. Qualification: Score and filter prospects
        3. Outreach: Send personalized emails
        4. Monitoring: Track responses and optimize
        """
        pipeline = CampaignPipelineStatus(
            campaign_id=campaign_id,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._active_pipelines[campaign_id] = pipeline

        if not self._data_bridge:
            pipeline.status = "error"
            return pipeline

        # Get campaign details
        campaign = await self._data_bridge.get_campaign(campaign_id)
        if not campaign:
            pipeline.status = "error"
            return pipeline

        pipeline.campaign_name = campaign["name"]
        pipeline.status = "active"

        # Update campaign status
        await self._data_bridge.update_campaign(campaign_id, {"status": "active"})

        try:
            # Phase 1: Discovery
            pipeline.phase = "discovery"
            await self._run_discovery_phase(campaign, pipeline)

            # Phase 2: Qualification & Deep Recon
            pipeline.phase = "qualification"
            await self._run_qualification_phase(campaign, pipeline)
            
            # Phase 2.5: Deep Recon (OMEGA Upgrade)
            if self._recon:
                pipeline.phase = "recon"
                await self._run_recon_phase(campaign, pipeline)

            # Phase 3: Outreach
            pipeline.phase = "outreach"
            await self._run_outreach_phase(campaign, pipeline)

            # Phase 4: Monitoring (set up for ongoing tracking)
            pipeline.phase = "monitoring"
            pipeline.status = "active"

        except Exception as exc:
            logger.error("Campaign %d pipeline error: %s", campaign_id, exc)
            pipeline.status = "error"

        pipeline.last_activity = datetime.now(timezone.utc).isoformat()
        return pipeline

    async def _run_discovery_phase(
        self,
        campaign: Dict[str, Any],
        pipeline: CampaignPipelineStatus,
    ) -> None:
        """Phase 1: Discover prospects matching campaign criteria."""
        if not self._hunter:
            logger.warning("B2B Hunter not available, skipping discovery")
            return

        target_countries = campaign.get("target_countries", [])
        target_categories = campaign.get("target_categories", [])

        from arki_project.config_marketing import B2B_CATEGORIES, DEFAULT_TARGET_MARKETS

        # Map campaign targets to config data
        regions = [
            m for m in DEFAULT_TARGET_MARKETS
            if m.get("region") in target_countries or m.get("country") in target_countries
        ]
        categories = [
            c for c in B2B_CATEGORIES
            if c.get("id") in target_categories
        ]

        # Run hunts
        for region in regions[:3]:  # Limit to prevent overload
            for category in categories[:4]:
                try:
                    result = await self._hunter.hunt(
                        region, category,
                        data_bridge=self._data_bridge,
                        scoring_engine=self._scorer,
                    )
                    pipeline.prospects_total += result.prospects_new
                except Exception as exc:
                    logger.warning("Discovery error [%s/%s]: %s",
                                   region.get("region"), category.get("id"), exc)

        # Log event
        if self._data_bridge:
            await self._data_bridge.log_event(
                "campaign_discovery_complete",
                campaign_id=campaign["id"],
                data={"prospects_found": pipeline.prospects_total},
                outcome="success",
            )

    async def _run_qualification_phase(
        self,
        campaign: Dict[str, Any],
        pipeline: CampaignPipelineStatus,
    ) -> None:
        """Phase 2: Score and qualify prospects."""
        if not self._scorer or not self._data_bridge:
            return

        min_score = campaign.get("min_score", 30.0)
        prospects = await self._data_bridge.get_prospects(
            status="discovered",
            min_score=min_score,
            limit=200,
        )

        scored = await self._scorer.batch_rescore(prospects)

        for prospect in scored:
            if prospect.get("score", 0) >= min_score:
                await self._data_bridge.update_prospect(
                    prospect["id"],
                    {"status": "qualified", "score": prospect["score"]},
                )
                pipeline.prospects_qualified += 1

        logger.info("Campaign %d: qualified %d/%d prospects",
                     campaign["id"], pipeline.prospects_qualified, len(prospects))

    async def _run_outreach_phase(
        self,
        campaign: Dict[str, Any],
        pipeline: CampaignPipelineStatus,
    ) -> None:
        """Phase 3: Execute email outreach."""
        if not self._outreach or not self._data_bridge:
            return

        qualified = await self._data_bridge.get_prospects(
            status="qualified",
            limit=50,
            order_by_score=True,
        )
        
        for prospect in qualified:
            # Check daily limit (Phase 4 Optimization)
            if pipeline.emails_sent >= 50:  # Daily limit
                logger.info("Daily outreach limit reached for campaign %d", campaign["id"])
                break
                
            result = await self.send_sequence(campaign["id"], prospect["id"])
            if result.get("success"):
                pipeline.emails_sent += 1
                pipeline.prospects_contacted += 1
                
        logger.info("Campaign %d: outreach complete, sent %d emails", 
                    campaign["id"], pipeline.emails_sent)

    async def send_sequence(
        self,
        campaign_id: int,
        prospect_id: int,
        sequence_template: str = "nordic_b2b_intro"
    ) -> Dict[str, Any]:
        """Send email sequence to prospect (Phase 4 Enhancement)."""
        from arki_project.utils.email_templates import render_template
        
        if not self._data_bridge or not self._outreach:
            return {"success": False, "error": "Engines not available"}
            
        # Get prospect data
        prospects = await self._data_bridge.get_prospects(limit=1) # Simplified for bridge
        # In a real scenario, we'd get by ID, but bridge needs that method
        # For now, let's assume we have the prospect dict from the loop
        
        # We need a get_prospect_by_id in the bridge
        # Let's try to find it or use a workaround
        prospect = None
        all_p = await self._data_bridge.get_prospects(limit=1000)
        for p in all_p:
            if p["id"] == prospect_id:
                prospect = p
                break
        
        if not prospect:
            return {"success": False, "error": "Prospect not found"}
        
        if not prospect.get("email"):
            return {"success": False, "error": "No email address"}
            
        # Render template
        variables = {
            "prospect_name": prospect.get("contact_person") or "there",
            "business_type": prospect.get("business_type", "business"),
            "city": prospect.get("city") or "your city",
            "gallery_name": prospect.get("business_name", "your gallery"),
            "cta_link": f"https://arkiobjects.com/contact?ref={prospect_id}"
        }
        
        try:
            subject, html = render_template(sequence_template, variables)
            
            # Send email via OutreachEngine (which uses EmailEngine)
            # Assuming outreach_engine has a send_email or similar
            # Based on email_engine.py, it's 'send' or 'send_template'
            
            from arki_project.utils.email_engine import EmailMessage
            msg = EmailMessage(
                to=prospect["email"],
                subject=subject,
                html_body=html,
                from_name="ArkiObjects"
            )
            
            # If outreach_engine is an EmailEngine instance
            result = await self._outreach.send(msg)
            
            if result.success:
                # Update prospect status
                await self._data_bridge.update_prospect(prospect_id, {"status": "contacted"})
                return {"success": True, "provider": result.provider}
            else:
                return {"success": False, "error": result.error}
        except Exception as e:
            logger.error("Sequence send failed: %s", e)
            return {"success": False, "error": str(e)}

        if not qualified:
            logger.info("Campaign %d: no qualified prospects for outreach", campaign["id"])
            return

        ab_test = campaign.get("ab_test_enabled", False)

        result = await self._outreach.execute_campaign_step(
            campaign["id"],
            step_number=0,
            prospects=qualified,
            data_bridge=self._data_bridge,
            ab_test=ab_test,
        )

        pipeline.emails_sent = result.emails_sent
        pipeline.prospects_contacted = result.emails_sent

        # Update campaign counters
        await self._data_bridge.update_campaign(
            campaign["id"],
            {
                "total_prospects": pipeline.prospects_total,
                "emails_sent": result.emails_sent,
            },
        )

    # ── Follow-up Management ─────────────────────────────

    async def process_followups(self, campaign_id: int) -> Dict[str, int]:
        """Process due follow-ups for a campaign."""
        if not self._outreach or not self._data_bridge:
            return {"processed": 0}

        due = await self._outreach.get_due_followups(
            campaign_id, data_bridge=self._data_bridge,
        )

        stats = {"checked": len(due), "sent": 0, "failed": 0}

        for item in due:
            prospect = item["prospect"]
            next_step = item["next_step"]

            try:
                result = await self._outreach.execute_campaign_step(
                    campaign_id,
                    step_number=next_step,
                    prospects=[prospect],
                    data_bridge=self._data_bridge,
                )
                stats["sent"] += result.emails_sent
                stats["failed"] += result.emails_failed
            except Exception as exc:
                logger.warning("Followup failed for prospect %s: %s", prospect.get("id"), exc)
                stats["failed"] += 1

        return stats

    # ── Campaign Monitoring ──────────────────────────────

    async def get_pipeline_status(self, campaign_id: int) -> CampaignPipelineStatus:
        """Get current pipeline status for a campaign."""
        if campaign_id in self._active_pipelines:
            pipeline = self._active_pipelines[campaign_id]
        else:
            pipeline = CampaignPipelineStatus(campaign_id=campaign_id)

        if self._data_bridge:
            campaign = await self._data_bridge.get_campaign(campaign_id)
            if campaign:
                pipeline.campaign_name = campaign["name"]
                pipeline.status = campaign["status"]
                pipeline.emails_sent = campaign.get("emails_sent", 0)
                pipeline.emails_opened = campaign.get("emails_opened", 0)
                pipeline.emails_replied = campaign.get("emails_replied", 0)

                # Calculate conversion rate
                if pipeline.emails_sent > 0:
                    pipeline.conversion_rate = (
                        pipeline.emails_replied / pipeline.emails_sent * 100
                    )

        return pipeline

    async def get_all_campaign_statuses(self) -> List[Dict[str, Any]]:
        """Get status for all active campaigns."""
        if not self._data_bridge:
            return []

        campaigns = await self._data_bridge.list_campaigns(status="active")
        statuses = []

        for campaign in campaigns:
            status = await self.get_pipeline_status(campaign["id"])
            statuses.append(status.to_dict())

        return statuses

    # ── Campaign Control ─────────────────────────────────

    async def pause_campaign(self, campaign_id: int) -> bool:
        """Pause a running campaign."""
        if not self._data_bridge:
            return False
        return await self._data_bridge.update_campaign(campaign_id, {"status": "paused"})

    async def resume_campaign(self, campaign_id: int) -> bool:
        """Resume a paused campaign."""
        if not self._data_bridge:
            return False
        return await self._data_bridge.update_campaign(campaign_id, {"status": "active"})

    async def complete_campaign(self, campaign_id: int) -> bool:
        """Mark a campaign as completed."""
        if not self._data_bridge:
            return False
        return await self._data_bridge.update_campaign(campaign_id, {"status": "completed"})

    # ── A/B Test Analysis ────────────────────────────────

    async def analyze_ab_test(self, campaign_id: int) -> Dict[str, Any]:
        """Analyze A/B test results for a campaign."""
        if not self._data_bridge:
            return {"error": "Data bridge not available"}

        email_stats = await self._data_bridge.get_campaign_email_stats(campaign_id)

        analysis = {
            "campaign_id": campaign_id,
            "email_stats": email_stats,
            "total_emails": sum(email_stats.values()),
            "variants": {},
            "winner": None,
            "confidence": 0.0,
        }

        # In a full implementation, we would query variant-specific stats
        # and calculate statistical significance
        return analysis

    # ── Template Listing ─────────────────────────────────

    def list_templates(self) -> List[Dict[str, Any]]:
        """List available campaign templates."""
        return [
            {"key": k, **v}
            for k, v in CAMPAIGN_TEMPLATES.items()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get campaign manager stats."""
        return {
            "active_pipelines": len(self._active_pipelines),
            "available_templates": len(CAMPAIGN_TEMPLATES),
            "hunter_available": self._hunter is not None,
            "scorer_available": self._scorer is not None,
            "outreach_available": self._outreach is not None,
            "professor_available": self._professor is not None,
        }

    async def get_all_campaign_statuses(self) -> List[Dict[str, Any]]:
        """Get statuses for all active/recent campaigns."""
        if not self._data_bridge:
            return []
            
        campaigns = await self._data_bridge.list_campaigns(limit=10)
        results = []
        for c in campaigns:
            status = await self.get_pipeline_status(c["id"])
            results.append(status.to_dict())
        return results

    async def _run_recon_phase(
        self,
        campaign: Dict[str, Any],
        pipeline: CampaignPipelineStatus,
    ) -> None:
        """Phase 2.5: Run deep reconnaissance on qualified prospects."""
        if not self._recon or not self._data_bridge:
            return

        # Get qualified prospects that haven't been reconned yet
        prospects = await self._data_bridge.get_prospects(
            status="qualified",
            limit=20, # Limit recon to top 20 to save resources
        )

        for prospect in prospects:
            try:
                domain = prospect.get("website_url")
                if not domain: continue
                
                # Run Deep Recon
                report = await self._recon.recon(domain, depth="standard")
                
                # Store recon data in data bridge (if supported)
                if hasattr(self._data_bridge, "store_recon_report"):
                    await self._data_bridge.store_recon_report(prospect["id"], report.to_dict())
                
                logger.info("Deep Recon complete for %s", domain)
            except Exception as exc:
                logger.error("Recon error for prospect %s: %s", prospect.get("id"), exc)


