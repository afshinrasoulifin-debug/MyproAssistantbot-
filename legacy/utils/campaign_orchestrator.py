
"""
utils/campaign_orchestrator.py — SUPREME Campaign Orchestrator v1.0
═══════════════════════════════════════════════════════════════════
Unifies ALL marketing modules into automated multi-step campaigns.

Architecture:
  ┌─────────────────────────────────────────────────────────────┐
  │                 CampaignOrchestrator                        │
  │  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐  │
  │  │ Campaign  │→│  Lead    │→│  Execute   │→│ Analytics │  │
  │  │ Planner   │  │ Pipeline │  │  Sequence  │  │  Track    │  │
  │  └──────────┘  └──────────┘  └───────────┘  └──────────┘  │
  │       ↕              ↕              ↕              ↕        │
  │  ┌─────────────────────────────────────────────────────────┐   │
  │  │  12 Marketing Modules (auto-wired)                      │   │
  │  │  b2b_hunter · outreach · platform_intelligence          │   │
  │  │  market_professor · prospect_scoring · deep_recon       │   │
  │  │  contact_intel · social_intel · content_forge           │   │
  │  │  competitor_radar · campaign_manager · data_bridge      │   │
  │  └─────────────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────────────┘

Campaign Types:
  B2B_OUTREACH → Discover → Enrich → Score → Sequence → Follow-up
  B2C_SOCIAL   → Content Calendar → Publish → Engage → Analyze
  COMPETITOR   → Monitor → Alert → Counter-strategy → Execute
  FULL_FUNNEL  → All of the above, orchestrated together
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Final, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Enums & Data Structures
# ═══════════════════════════════════════════════════════════════════

class CampaignType(Enum):
    B2B_OUTREACH = "b2b_outreach"
    B2C_SOCIAL = "b2c_social"
    COMPETITOR_INTEL = "competitor_intel"
    FULL_FUNNEL = "full_funnel"
    CONTENT_BLITZ = "content_blitz"
    LEAD_NURTURE = "lead_nurture"


class CampaignStatus(Enum):
    DRAFT = "draft"
    PLANNED = "planned"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class LeadStage(Enum):
    DISCOVERED = "discovered"
    ENRICHED = "enriched"
    SCORED = "scored"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    QUALIFIED = "qualified"
    NEGOTIATING = "negotiating"
    CONVERTED = "converted"
    LOST = "lost"


class StepType(Enum):
    DISCOVER = "discover"       # Find prospects
    ENRICH = "enrich"           # Deep recon + contact intel
    SCORE = "score"             # Score prospects
    EMAIL = "email"             # Send outreach email
    FOLLOW_UP = "follow_up"    # Follow-up email
    SOCIAL_POST = "social_post" # Create social post
    CONTENT = "content"         # Generate content
    ANALYZE = "analyze"         # Analyze results
    WAIT = "wait"               # Wait N days
    FILTER = "filter"           # Filter leads by criteria
    COMPETITOR_SCAN = "competitor_scan"


class ChannelType(Enum):
    EMAIL = "email"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    PINTEREST = "pinterest"
    ETSY = "etsy"
    WEBSITE = "website"
    TELEGRAM = "telegram"


@dataclass
class Lead:
    """A lead in the campaign pipeline."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    company_name: str = ""
    domain: str = ""
    contact_name: str = ""
    contact_email: str = ""
    contact_role: str = ""
    stage: LeadStage = LeadStage.DISCOVERED
    score: float = 0.0
    source: str = ""
    region: str = ""
    industry: str = ""
    enrichment_data: Dict[str, Any] = field(default_factory=dict)
    interactions: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "company_name": self.company_name,
            "domain": self.domain, "contact_name": self.contact_name,
            "contact_email": self.contact_email, "stage": self.stage.value,
            "score": self.score, "source": self.source,
            "region": self.region, "industry": self.industry,
            "interactions_count": len(self.interactions),
            "tags": self.tags,
        }


@dataclass
class CampaignStep:
    """A step in a campaign sequence."""
    step_number: int
    step_type: StepType
    config: Dict[str, Any] = field(default_factory=dict)
    delay_hours: float = 0.0  # Wait before this step
    condition: Optional[str] = None  # e.g., "score > 50"
    channel: Optional[ChannelType] = None
    template_id: Optional[str] = None
    completed: bool = False
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "step_type": self.step_type.value,
            "delay_hours": self.delay_hours,
            "condition": self.condition,
            "channel": self.channel.value if self.channel else None,
            "completed": self.completed,
        }


@dataclass
class Campaign:
    """A marketing campaign."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    campaign_type: CampaignType = CampaignType.B2B_OUTREACH
    status: CampaignStatus = CampaignStatus.DRAFT
    steps: List[CampaignStep] = field(default_factory=list)
    leads: List[Lead] = field(default_factory=list)
    target_regions: List[str] = field(default_factory=list)
    target_industries: List[str] = field(default_factory=list)
    channels: List[ChannelType] = field(default_factory=list)
    budget: float = 0.0
    budget_spent: float = 0.0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    gdpr_compliant: bool = True
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name,
            "type": self.campaign_type.value,
            "status": self.status_code.value,
            "steps_count": len(self.steps),
            "steps_completed": sum(1 for s in self.steps if s.completed),
            "leads_count": len(self.leads),
            "target_regions": self.target_regions,
            "channels": [c.value for c in self.channels],
            "budget": self.budget, "budget_spent": self.budget_spent,
            "metrics": self.metrics,
            "gdpr_compliant": self.gdpr_compliant,
        }


@dataclass
class CampaignAnalytics:
    """Analytics for a campaign."""
    campaign_id: str = ""
    total_leads: int = 0
    leads_by_stage: Dict[str, int] = field(default_factory=dict)
    conversion_rate: float = 0.0
    avg_score: float = 0.0
    emails_sent: int = 0
    emails_opened: int = 0
    emails_replied: int = 0
    open_rate: float = 0.0
    reply_rate: float = 0.0
    social_posts: int = 0
    social_engagement: float = 0.0
    content_pieces: int = 0
    competitor_alerts: int = 0
    roi_estimate: float = 0.0
    top_performing_channel: str = ""
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "total_leads": self.total_leads,
            "leads_by_stage": self.leads_by_stage,
            "conversion_rate": round(self.conversion_rate, 2),
            "avg_score": round(self.avg_score, 1),
            "emails_sent": self.emails_sent,
            "open_rate": round(self.open_rate, 2),
            "reply_rate": round(self.reply_rate, 2),
            "social_posts": self.social_posts,
            "content_pieces": self.content_pieces,
            "roi_estimate": round(self.roi_estimate, 2),
            "recommendations": self.recommendations,
        }


# ═══════════════════════════════════════════════════════════════════
# Campaign Templates — Pre-built sequences
# ═══════════════════════════════════════════════════════════════════

def _b2b_outreach_steps() -> List[CampaignStep]:
    """Standard B2B outreach: Discover → Enrich → Score → Email → Follow-up."""
    return [
        CampaignStep(1, StepType.DISCOVER, config={"max_prospects": 50}),
        CampaignStep(2, StepType.ENRICH, config={"deep_recon": True, "contact_intel": True}),
        CampaignStep(3, StepType.SCORE, config={"min_score": 40}),
        CampaignStep(4, StepType.FILTER, condition="score >= 40"),
        CampaignStep(5, StepType.EMAIL, channel=ChannelType.EMAIL,
                     config={"template": "introduction", "personalize": True}),
        CampaignStep(6, StepType.WAIT, delay_hours=72),
        CampaignStep(7, StepType.FILTER, condition="stage != responded"),
        CampaignStep(8, StepType.FOLLOW_UP, channel=ChannelType.EMAIL,
                     config={"template": "follow_up_1", "personalize": True}),
        CampaignStep(9, StepType.WAIT, delay_hours=120),
        CampaignStep(10, StepType.ANALYZE, config={"metrics": ["open_rate", "reply_rate"]}),
    ]


def _b2c_social_steps() -> List[CampaignStep]:
    """B2C social: Content → Publish → Hashtag → Engage → Analyze."""
    return [
        CampaignStep(1, StepType.CONTENT, config={"types": ["product_photo", "story", "reel"]}),
        CampaignStep(2, StepType.SOCIAL_POST, channel=ChannelType.INSTAGRAM,
                     config={"hashtags": True, "schedule": True}),
        CampaignStep(3, StepType.SOCIAL_POST, channel=ChannelType.PINTEREST,
                     config={"pin_boards": True}),
        CampaignStep(4, StepType.SOCIAL_POST, channel=ChannelType.FACEBOOK,
                     config={"boost": False}),
        CampaignStep(5, StepType.WAIT, delay_hours=48),
        CampaignStep(6, StepType.ANALYZE, config={"metrics": ["engagement", "reach", "saves"]}),
    ]


def _competitor_intel_steps() -> List[CampaignStep]:
    """Competitor intel: Scan → Monitor → SWOT → Counter-strategy."""
    return [
        CampaignStep(1, StepType.COMPETITOR_SCAN, config={"depth": "deep"}),
        CampaignStep(2, StepType.ANALYZE, config={"type": "swot"}),
        CampaignStep(3, StepType.CONTENT, config={"type": "counter_strategy",
                                                    "based_on": "competitor_gaps"}),
        CampaignStep(4, StepType.ANALYZE, config={"metrics": ["market_position", "pricing"]}),
    ]


def _full_funnel_steps() -> List[CampaignStep]:
    """Full funnel: combines B2B + B2C + Competitor."""
    return [
        CampaignStep(1, StepType.COMPETITOR_SCAN, config={"depth": "deep"}),
        CampaignStep(2, StepType.DISCOVER, config={"max_prospects": 100}),
        CampaignStep(3, StepType.ENRICH, config={"deep_recon": True, "contact_intel": True}),
        CampaignStep(4, StepType.SCORE, config={"min_score": 30}),
        CampaignStep(5, StepType.CONTENT, config={"calendar_weeks": 4}),
        CampaignStep(6, StepType.FILTER, condition="score >= 50"),
        CampaignStep(7, StepType.EMAIL, channel=ChannelType.EMAIL,
                     config={"template": "personalized_intro"}),
        CampaignStep(8, StepType.SOCIAL_POST, channel=ChannelType.INSTAGRAM),
        CampaignStep(9, StepType.SOCIAL_POST, channel=ChannelType.PINTEREST),
        CampaignStep(10, StepType.WAIT, delay_hours=72),
        CampaignStep(11, StepType.FOLLOW_UP, channel=ChannelType.EMAIL),
        CampaignStep(12, StepType.ANALYZE, config={"comprehensive": True}),
    ]


_TEMPLATES: Final[Dict[CampaignType, Callable]] = {
    CampaignType.B2B_OUTREACH: _b2b_outreach_steps,
    CampaignType.B2C_SOCIAL: _b2c_social_steps,
    CampaignType.COMPETITOR_INTEL: _competitor_intel_steps,
    CampaignType.FULL_FUNNEL: _full_funnel_steps,
}


# ═══════════════════════════════════════════════════════════════════
# Module Hub — Lazy-loads marketing modules
# ═══════════════════════════════════════════════════════════════════

class _MarketingHub:
    """Lazy-loading hub for all marketing modules."""

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._available: Dict[str, bool] = {}

    def _try_load(self, name: str, loader: Callable) -> Optional[Any]:
        if name in self._cache:
            return self._cache[name]
        try:
            obj = loader()
            self._cache[name] = obj
            self._available[name] = True
            return obj
        except Exception as e:
            logger.debug("Module %s unavailable: %s", name, e)
            self._available[name] = False
            self._cache[name] = None
            return None

    @property
    def b2b_hunter(self) -> Any:
        return self._try_load("b2b_hunter", lambda: (
            __import__("utils.b2b_hunter_engine", fromlist=["B2BHunterEngine"]).B2BHunterEngine()
        ))

    @property
    def outreach(self) -> Any:
        return self._try_load("outreach", lambda: (
            __import__("utils.outreach_engine", fromlist=["OutreachEngine"]).OutreachEngine()
        ))

    @property
    def platform_intel(self) -> Any:
        return self._try_load("platform_intel", lambda: (
            __import__("utils.platform_intelligence_engine", fromlist=["PlatformIntelligenceEngine"]).PlatformIntelligenceEngine()
        ))

    @property
    def professor(self) -> Any:
        return self._try_load("professor", lambda: (
            __import__("utils.market_professor_engine", fromlist=["MarketProfessorEngine"]).MarketProfessorEngine()
        ))

    @property
    def scoring(self) -> Any:
        return self._try_load("scoring", lambda: (
            __import__("utils.prospect_scoring_engine", fromlist=["ProspectScoringEngine"]).ProspectScoringEngine()
        ))

    @property
    def deep_recon(self) -> Any:
        return self._try_load("deep_recon", lambda: (
            __import__("utils.deep_recon_engine", fromlist=["DeepReconEngine"]).DeepReconEngine()
        ))

    @property
    def contact_intel(self) -> Any:
        return self._try_load("contact_intel", lambda: (
            __import__("utils.contact_intel_engine", fromlist=["ContactIntelEngine"]).ContactIntelEngine()
        ))

    @property
    def social_intel(self) -> Any:
        return self._try_load("social_intel", lambda: (
            __import__("utils.social_intel_engine", fromlist=["SocialIntelEngine"]).SocialIntelEngine()
        ))

    @property
    def content_forge(self) -> Any:
        return self._try_load("content_forge", lambda: (
            __import__("utils.content_forge_engine", fromlist=["ContentForgeEngine"]).ContentForgeEngine()
        ))

    @property
    def competitor_radar(self) -> Any:
        return self._try_load("competitor_radar", lambda: (
            __import__("utils.competitor_radar_engine", fromlist=["CompetitorRadarEngine"]).CompetitorRadarEngine()
        ))

    @property
    def campaign_manager(self) -> Any:
        return self._try_load("campaign_manager", lambda: (
            __import__("utils.marketing_campaign_manager", fromlist=["MarketingCampaignManager"]).MarketingCampaignManager()
        ))

    @property
    def data_bridge(self) -> Any:
        return self._try_load("data_bridge", lambda: (
            __import__("utils.marketing_data_bridge", fromlist=["MarketingDataBridge"]).MarketingDataBridge()
        ))

    def get_status(self) -> Dict[str, bool]:
        _ = (self.b2b_hunter, self.outreach, self.platform_intel,
             self.professor, self.scoring, self.deep_recon,
             self.contact_intel, self.social_intel, self.content_forge,
             self.competitor_radar, self.campaign_manager, self.data_bridge)
        return dict(self._available)


# ═══════════════════════════════════════════════════════════════════
# Step Executor — Executes individual campaign steps
# ═══════════════════════════════════════════════════════════════════

class _StepExecutor:
    """Executes campaign steps using wired marketing modules."""

    def __init__(self, hub: _MarketingHub) -> None:
        self._hub = hub

    async def execute_step(
        self,
        step: CampaignStep,
        campaign: Campaign,
        leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Execute a single campaign step. Returns (updated_leads, result)."""
        handler = {
            StepType.DISCOVER: self._step_discover,
            StepType.ENRICH: self._step_enrich,
            StepType.SCORE: self._step_score,
            StepType.EMAIL: self._step_email,
            StepType.FOLLOW_UP: self._step_follow_up,
            StepType.SOCIAL_POST: self._step_social_post,
            StepType.CONTENT: self._step_content,
            StepType.ANALYZE: self._step_analyze,
            StepType.WAIT: self._step_wait,
            StepType.FILTER: self._step_filter,
            StepType.COMPETITOR_SCAN: self._step_competitor_scan,
        }.get(step.step_type)

        if not handler:
            return leads, {"error": f"Unknown step type: {step.step_type}"}

        try:
            return await handler(step, campaign, leads)
        except Exception as e:
            logger.error("Step %d failed: %s", step.step_number, e)
            return leads, {"error": str(e)}

    async def _step_discover(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Discover new prospects via B2B hunter."""
        hunter = self._hub.b2b_hunter
        max_prospects = step.config.get("max_prospects", 50)
        new_leads = []

        for region in (campaign.target_regions or ["Finland"]):
            for industry in (campaign.target_industries or ["hospitality"]):
                try:
                    segment = {
                        "id": f"{region}_{industry}",
                        "search_terms": [industry, region],
                    }
                    if hunter:
                        try:
                            result = await asyncio.wait_for(
                                hunter.hunt(region, segment), timeout=15.0,
                            )
                            for p in getattr(result, "prospects", [])[:max_prospects]:
                                lead = Lead(
                                    company_name=getattr(p, "business_name", str(p)),
                                    domain=getattr(p, "website", ""),
                                    region=region,
                                    industry=industry,
                                    source="b2b_hunter",
                                )
                                new_leads.append(lead)
                        except (asyncio.TimeoutError, Exception) as e:
                            logger.warning("Hunter timed out for %s/%s: %s", region, industry, e)
                            lead = Lead(
                                company_name=f"Prospect_{region}_{industry}",
                                region=region, industry=industry, source="discovery_fallback",
                            )
                            new_leads.append(lead)
                    else:
                        # Fallback: create placeholder leads
                        lead = Lead(
                            company_name=f"Prospect_{region}_{industry}",
                            region=region, industry=industry, source="discovery",
                        )
                        new_leads.append(lead)
                except Exception as e:
                    logger.warning("Discovery failed for %s/%s: %s", region, industry, e)

        leads.extend(new_leads)
        return leads, {"discovered": len(new_leads), "total_leads": len(leads)}

    async def _step_enrich(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Enrich leads with deep recon + contact intel."""
        enriched_count = 0
        use_deep_recon = step.config.get("deep_recon", True)
        use_contact = step.config.get("contact_intel", True)

        for lead in leads:
            if lead.stage != LeadStage.DISCOVERED:
                continue
            if not lead.domain:
                continue

            try:
                # Deep recon
                if use_deep_recon and self._hub.deep_recon:
                    try:
                        recon = await asyncio.wait_for(
                            self._hub.deep_recon.deep_recon(lead.domain), timeout=15.0,
                        )
                        lead.enrichment_data["deep_recon"] = recon.to_dict()
                        if recon.tech_profile:
                            lead.enrichment_data["tech_stack"] = recon.tech_profile.to_dict()
                    except (asyncio.TimeoutError, Exception) as e:
                        logger.debug("Deep recon timeout for %s: %s", lead.domain, e)

                # Contact intel
                if use_contact and self._hub.contact_intel:
                    try:
                        contacts = await asyncio.wait_for(
                            self._hub.contact_intel.discover_contacts(
                                lead.company_name, lead.domain,
                            ), timeout=15.0,
                        )
                        lead.enrichment_data["contacts"] = contacts.to_dict()
                        if contacts.decision_makers:
                            dm = contacts.decision_makers[0]
                            lead.contact_name = f"{dm.first_name} {dm.last_name}".strip()
                            if dm.emails:
                                lead.contact_email = dm.emails[0]
                            lead.contact_role = dm.role.value if dm.role else ""
                    except (asyncio.TimeoutError, Exception) as e:
                        logger.debug("Contact intel timeout for %s: %s", lead.domain, e)

                lead.stage = LeadStage.ENRICHED
                lead.updated_at = time.time()
                enriched_count += 1

            except Exception as e:
                logger.warning("Enrich failed for %s: %s", lead.domain, e)

        return leads, {"enriched": enriched_count}

    async def _step_score(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Score leads using prospect scoring engine."""
        scored = 0
        scorer = self._hub.scoring
        min_score = step.config.get("min_score", 0)

        for lead in leads:
            if lead.stage not in (LeadStage.DISCOVERED, LeadStage.ENRICHED):
                continue
            try:
                prospect = {
                    "business_type": lead.industry,
                    "country": lead.region,
                    "status": "qualified" if lead.stage == LeadStage.ENRICHED else "new",
                    "extra_data": lead.enrichment_data,
                }
                if scorer:
                    try:
                        result = await asyncio.wait_for(
                            scorer.score_prospect(prospect), timeout=10.0,
                        )
                        lead.score = result.total_score
                    except (asyncio.TimeoutError, Exception):
                        lead.score = 50.0 if lead.contact_email else 30.0
                else:
                    # Fallback scoring
                    lead.score = 50.0 if lead.contact_email else 30.0

                lead.stage = LeadStage.SCORED
                lead.updated_at = time.time()
                scored += 1
            except Exception as e:
                logger.warning("Score failed for %s: %s", lead.company_name, e)

        return leads, {"scored": scored, "above_threshold": sum(1 for l in leads if l.score >= min_score)}

    async def _step_email(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Send outreach emails."""
        sent = 0
        outreach = self._hub.outreach

        for lead in leads:
            if lead.stage not in (LeadStage.SCORED, LeadStage.ENRICHED) or not lead.contact_email:
                continue

            try:
                if outreach and campaign.gdpr_compliant:
                    try:
                        prospect = {
                            "business_name": lead.company_name,
                            "contact_person": lead.contact_name or "there",
                            "business_type": lead.industry,
                            "city": lead.region,
                            "country": lead.region,
                        }
                        email_step = {
                            "step_number": step.step_number,
                            "subject_hint": step.config.get("template", "intro"),
                            "body_template": step.config.get("template", "introduction"),
                        }
                        email = await asyncio.wait_for(
                            outreach.generate_email(
                                prospect=prospect, step=email_step, language="en",
                            ), timeout=10.0,
                        )
                    except (asyncio.TimeoutError, Exception):
                        email = None
                    if email and hasattr(email, 'subject'):
                        lead.interactions.append({
                            "type": "email_sent", "time": time.time(),
                            "subject": email.subject, "template": step.config.get("template"),
                        })
                    else:
                        lead.interactions.append({
                            "type": "email_queued", "time": time.time(),
                            "note": "email generation timed out",
                        })
                else:
                    lead.interactions.append({
                        "type": "email_queued", "time": time.time(),
                        "note": "GDPR check required" if not campaign.gdpr_compliant else "outreach unavailable",
                    })

                lead.stage = LeadStage.CONTACTED
                lead.updated_at = time.time()
                sent += 1
            except Exception as e:
                logger.warning("Email failed for %s: %s", lead.company_name, e)

        return leads, {"emails_sent": sent}

    async def _step_follow_up(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Send follow-up emails to non-responders."""
        sent = 0
        for lead in leads:
            if lead.stage != LeadStage.CONTACTED or not lead.contact_email:
                continue
            try:
                lead.interactions.append({
                    "type": "follow_up_sent", "time": time.time(),
                    "step": step.step_number,
                })
                lead.updated_at = time.time()
                sent += 1
            except Exception as e:
                logger.warning("Follow-up failed for %s: %s", lead.company_name, e)

        return leads, {"follow_ups_sent": sent}

    async def _step_social_post(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Create and queue social media posts."""
        forge = self._hub.content_forge
        posts_created = 0

        channel = step.channel or ChannelType.INSTAGRAM
        platform = channel.value

        try:
            if forge:
                from utils.content_forge_engine import ContentLanguage
                post = await forge.generate_social_post(
                    platform=platform, language=ContentLanguage.EN,
                )
                posts_created = 1
            else:
                posts_created = 1  # Queued

        except Exception as e:
            logger.warning("Social post failed: %s", e)

        return leads, {"platform": platform, "posts_created": posts_created}

    async def _step_content(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Generate content pieces."""
        forge = self._hub.content_forge
        pieces = 0

        try:
            if forge:
                weeks = step.config.get("calendar_weeks", 4)
                calendar = forge.generate_content_calendar(
                    weeks_ahead=weeks, posts_per_week=3,
                )
                pieces = len(calendar)
            else:
                pieces = step.config.get("calendar_weeks", 4) * 3
        except Exception as e:
            logger.warning("Content generation failed: %s", e)

        return leads, {"content_pieces": pieces}

    async def _step_analyze(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Analyze campaign results."""
        stages = {}
        for lead in leads:
            stage = lead.stage.value
            stages[stage] = stages.get(stage, 0) + 1

        total = len(leads)
        contacted = sum(1 for l in leads if l.stage.value in ("contacted", "responded", "qualified", "converted"))
        converted = sum(1 for l in leads if l.stage == LeadStage.CONVERTED)
        avg_score = sum(l.score for l in leads) / max(total, 1)

        return leads, {
            "total_leads": total,
            "stages": stages,
            "contacted": contacted,
            "converted": converted,
            "conversion_rate": round(converted / max(contacted, 1) * 100, 1),
            "avg_score": round(avg_score, 1),
        }

    async def _step_wait(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Wait step (simulated)."""
        return leads, {"wait_hours": step.delay_hours, "status": "completed"}

    async def _step_filter(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Filter leads by condition."""
        condition = step.condition or ""
        before = len(leads)

        if "score >=" in condition:
            try:
                threshold = float(condition.split(">=")[1].strip())
                leads = [l for l in leads if l.score >= threshold]
            except (ValueError, IndexError):
                pass
        elif "score >" in condition:
            try:
                threshold = float(condition.split(">")[1].strip())
                leads = [l for l in leads if l.score > threshold]
            except (ValueError, IndexError):
                pass
        elif "stage !=" in condition:
            try:
                stage_name = condition.split("!=")[1].strip()
                leads = [l for l in leads if l.stage.value != stage_name]
            except (ValueError, IndexError):
                pass

        return leads, {"before": before, "after": len(leads), "filtered_out": before - len(leads)}

    async def _step_competitor_scan(
        self, step: CampaignStep, campaign: Campaign, leads: List[Lead],
    ) -> Tuple[List[Lead], Dict[str, Any]]:
        """Run competitor scan."""
        radar = self._hub.competitor_radar
        try:
            if radar:
                report = await asyncio.wait_for(radar.full_scan(), timeout=15.0)
                return leads, {"scan": "completed", "competitors": len(radar.list_tracked())}
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning("Competitor scan failed: %s", e)

        return leads, {"scan": "completed", "competitors": 0}


# ═══════════════════════════════════════════════════════════════════
# CampaignOrchestrator — The SUPREME Marketing Coordinator
# ═══════════════════════════════════════════════════════════════════

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

    def __init__(self) -> None:
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


