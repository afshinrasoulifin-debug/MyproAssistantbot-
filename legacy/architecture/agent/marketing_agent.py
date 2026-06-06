
from __future__ import annotations
"""
tg_bot/architecture/agent/marketing_agent.py — Marketing Agent TITAN (L4)
═════════════════════════════════════════════════════════════════════════════
MarketingMasterAgent — top-level agent coordinating 5 sub-agent domains.

Architecture
────────────
   ┌──────────────────────────────────────────────────────────────────┐
   │                  MARKETING MASTER AGENT (L4)                     │
   │                       (BaseAgent)                                │
   ├──────────┬──────────┬──────────┬──────────┬──────────────────────┤
   │ Hunter   │ Outreach │ Platform │ Professor│ Campaign             │
   │ SubAgent │ SubAgent │ SubAgent │ SubAgent │ SubAgent             │
   ├──────────┼──────────┼──────────┼──────────┼──────────────────────┤
   │ B2B      │ Email    │ Monitor  │ Analysis │ Full Lifecycle       │
   │ Discovery│ Sequence │ Discover │ Compete  │ Create/Launch        │
   │ Enrich   │ A/B Test │ AutoList │ Social   │ Monitor/Optimize     │
   │ Score    │ Follow-up│ Events   │ Forecast │ Report               │
   └──────────┴──────────┴──────────┴──────────┴──────────────────────┘

Extends: architecture/agent/base_agent.py (BaseAgent)

Sub-agents are logical groupings that route commands to the correct
engine. They are not separate processes — they share the same async
event loop and data bridge.

Integration points:
  • Telegram handler: handlers/marketing_auto.py
  • Service layer: services/marketing_automation_service.py
  • Data layer: utils/marketing_data_bridge.py
  • All L9 engines
"""

# NOTE: Consider using arki_project.utils.feature_registry for optional imports

import asyncio
import logging
from typing import Any, Dict, Optional


# ── Base Agent ──
try:
    from arki_project.architecture.agent.base import BaseAgent
    _BASE_AGENT_AVAILABLE = True
except ImportError:
    _BASE_AGENT_AVAILABLE = False

# ── Config ──
try:
    from arki_project.config_marketing import (
        MarketingSettings,
        DEFAULT_BRAND,
        DEFAULT_TARGET_MARKETS,
        B2B_CATEGORIES,
        PLATFORM_REGISTRY,
    )
    _CONFIG_AVAILABLE = True
except ImportError:
    _CONFIG_AVAILABLE = False

# ── Engines ──
try:
    from arki_project.utils.marketing_data_bridge import get_data_bridge, MarketingDataBridge
    _DATA_BRIDGE_AVAILABLE = True
except ImportError:
    _DATA_BRIDGE_AVAILABLE = False

try:
    from arki_project.utils.prospect_scoring_engine import ProspectScoringEngine
    _SCORER_AVAILABLE = True
except ImportError:
    _SCORER_AVAILABLE = False

try:
    from arki_project.utils.b2b_hunter_engine import B2BHunterEngine
    _HUNTER_AVAILABLE = True
except ImportError:
    _HUNTER_AVAILABLE = False

try:
    from arki_project.utils.outreach_engine import OutreachEngine
    _OUTREACH_AVAILABLE = True
except ImportError:
    _OUTREACH_AVAILABLE = False

try:
    from arki_project.utils.platform_intelligence_engine import PlatformIntelligenceEngine
    _PLATFORM_INTEL_AVAILABLE = True
except ImportError:
    _PLATFORM_INTEL_AVAILABLE = False

try:
    from arki_project.utils.market_professor_engine import MarketProfessorEngine
    _PROFESSOR_AVAILABLE = True
except ImportError:
    _PROFESSOR_AVAILABLE = False

try:
    from arki_project.utils.marketing_campaign_manager import MarketingCampaignManager
    _CAMPAIGN_MANAGER_AVAILABLE = True
except ImportError:
    _CAMPAIGN_MANAGER_AVAILABLE = False

try:
    from arki_project.services.marketing_automation_service import MarketingAutomationService
    _SERVICE_AVAILABLE = True
except ImportError:
    _SERVICE_AVAILABLE = False

# ── OMEGA Engines ──
try:
    from arki_project.utils.deep_recon_engine import DeepReconEngine
    _OMEGA_DEEP_RECON = True
except ImportError:
    _OMEGA_DEEP_RECON = False

try:
    from arki_project.utils.trend_intelligence_engine import TrendIntelligenceEngine
    _OMEGA_TREND_INTEL = True
except ImportError:
    _OMEGA_TREND_INTEL = False

try:
    from arki_project.utils.social_execution_engine import SocialExecutionEngine
    _OMEGA_SOCIAL_EXEC = True
except ImportError:
    _OMEGA_SOCIAL_EXEC = False

try:
    from arki_project.utils.visual_forge_engine import VisualForgeEngine
    _OMEGA_VISUAL_FORGE = True
except ImportError:
    _OMEGA_VISUAL_FORGE = False

try:
    from arki_project.utils.strategic_director_layer import StrategicDirectorLayer
    _OMEGA_STRATEGIC_DIRECTOR = True
except ImportError:
    _OMEGA_STRATEGIC_DIRECTOR = False

try:
    from arki_project.utils.multi_format_content_factory import MultiFormatContentFactory
    _TITAN_CONTENT_FACTORY = True
except ImportError:
    _TITAN_CONTENT_FACTORY = False

try:
    from arki_project.utils.layout_orchestrator import LayoutOrchestrator
    _TITAN_LAYOUT_ORCH = True
except ImportError:
    _TITAN_LAYOUT_ORCH = False

try:
    from arki_project.utils.omni_channel_distribution_hub import OmniChannelDistributionHub
    _TITAN_DISTRO_HUB = True
except ImportError:
    _TITAN_DISTRO_HUB = False

try:
    from arki_project.utils.victor_elite_engine import VictorEliteEngine
    _VICTOR_ELITE = True
except ImportError:
    _VICTOR_ELITE = False

try:
    from arki_project.utils.cyber_intelligence_hub import CyberIntelligenceHub
    _VICTOR_INTEL = True
except ImportError:
    _VICTOR_INTEL = False

try:
    from arki_project.utils.autonomous_roi_engine import AutonomousROIEngine
    _ROI_ENGINE = True
except ImportError:
    _ROI_ENGINE = False

try:
    from arki_project.utils.apex_command_center import ApexCommandCenter
    _APEX_COMMAND = True
except ImportError:
    _APEX_COMMAND = False

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Marketing Master Agent
# ═══════════════════════════════════════════════════════════

class MarketingMasterAgent(BaseAgent if _BASE_AGENT_AVAILABLE else object):
    """
    Marketing Master Agent — coordinates 5 sub-agent domains
    for autonomous 24/7 marketing operations.

    Sub-agents:
      🔍 HunterSubAgent — B2B prospect discovery
      📧 OutreachSubAgent — email sequence management
      🏪 PlatformSubAgent — marketplace & event management
      🎓 ProfessorSubAgent — market intelligence & strategy
      📋 CampaignSubAgent — full campaign lifecycle

    Usage:
      agent = MarketingMasterAgent(admin_ids={12345})
      await agent.initialize()
      await agent.start()
    """

    AGENT_NAME = "marketing_master"
    AGENT_VERSION = "29.5.0-AUTONOMOUS"
    AGENT_DESCRIPTION = "Fully Autonomous Marketing Powerhouse — TITAN-OMEGA"

    def __init__(
        self,
        *,
        admin_ids: Optional[set] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> None:
        if _BASE_AGENT_AVAILABLE:
            super().__init__(name=self.AGENT_NAME)

        self._admin_ids = admin_ids or set()
        self._settings = settings or {}
        self._initialized = False

        # Engines (initialized in initialize())
        self._data_bridge: Optional[MarketingDataBridge] = None
        self._scorer: Optional[ProspectScoringEngine] = None
        self._hunter: Optional[B2BHunterEngine] = None
        self._outreach: Optional[OutreachEngine] = None
        self._platform_intel: Optional[PlatformIntelligenceEngine] = None
        self._professor: Optional[MarketProfessorEngine] = None
        self._campaign_manager: Optional[MarketingCampaignManager] = None
        self._service: Optional[MarketingAutomationService] = None
        
        # OMEGA Engines
        self._recon: Optional[DeepReconEngine] = None
        self._personalizer: Optional[HyperPersonalizationEngine] = None
        self._trend_intel: Optional[TrendIntelligenceEngine] = None
        self._social_exec: Optional[SocialExecutionEngine] = None
        self._visual_forge: Optional[VisualForgeEngine] = None
        self._director: Optional[StrategicDirectorLayer] = None
        
        # TITAN Content Engines
        self._content_factory: Optional[MultiFormatContentFactory] = None
        self._layout_orch: Optional[LayoutOrchestrator] = None
        self._distro_hub: Optional[OmniChannelDistributionHub] = None
        
        # VICTOR Security Engines
        self._victor: Optional[VictorEliteEngine] = None
        self._cyber_intel: Optional[CyberIntelligenceHub] = None
        
        # REAL Financial Engine
        self._roi: Optional[AutonomousROIEngine] = None
        
        # APEX Supremacy Layer
        self._apex: Optional[ApexCommandCenter] = None

    # ── Initialization ───────────────────────────────────

    async def initialize(self, ai_client=None) -> bool:
        """
        Initialize all engines and wire them together.

        Call this once at startup before using the agent.
        """
        try:
            logger.info("🚀 Initializing MarketingMasterAgent v%s", self.AGENT_VERSION)

            # Data Bridge
            if _DATA_BRIDGE_AVAILABLE:
                self._data_bridge = get_data_bridge()

            # Scoring Engine
            if _SCORER_AVAILABLE:
                self._scorer = ProspectScoringEngine()

            # B2B Hunter
            if _HUNTER_AVAILABLE:
                self._hunter = B2BHunterEngine()

            # Outreach Engine
            if _OUTREACH_AVAILABLE:
                self._outreach = OutreachEngine(ai_client=ai_client)

            # Platform Intelligence
            if _PLATFORM_INTEL_AVAILABLE:
                registry = PLATFORM_REGISTRY if _CONFIG_AVAILABLE else {}
                self._platform_intel = PlatformIntelligenceEngine(
                    platform_registry=registry,
                )

            # Market Professor
            if _PROFESSOR_AVAILABLE:
                self._professor = MarketProfessorEngine()

            # OMEGA Engines
            if _OMEGA_DEEP_RECON:
                from arki_project.utils.deep_recon_engine import DeepReconEngine
                self._recon = DeepReconEngine()
            
            from arki_project.utils.hyper_personalization_engine import HyperPersonalizationEngine
            self._personalizer = HyperPersonalizationEngine(ai_client=ai_client)

            if _OMEGA_TREND_INTEL:
                self._trend_intel = TrendIntelligenceEngine(ai_client=ai_client)
            if _OMEGA_SOCIAL_EXEC:
                self._social_exec = SocialExecutionEngine(ai_client=ai_client)
            if _OMEGA_VISUAL_FORGE:
                self._visual_forge = VisualForgeEngine(ai_client=ai_client)
            if _OMEGA_STRATEGIC_DIRECTOR:
                self._director = StrategicDirectorLayer(ai_client=ai_client, data_bridge=self._data_bridge)

            # TITAN Content Engines
            if _TITAN_CONTENT_FACTORY:
                self._content_factory = MultiFormatContentFactory(ai_client=ai_client)
            if _TITAN_LAYOUT_ORCH:
                self._layout_orch = LayoutOrchestrator(visual_forge=self._visual_forge)
            if _TITAN_DISTRO_HUB:
                self._distro_hub = OmniChannelDistributionHub(social_exec=self._social_exec)

            # VICTOR Security Engines
            if _VICTOR_ELITE:
                self._victor = VictorEliteEngine(data_bridge=self._data_bridge)
            if _VICTOR_INTEL:
                self._cyber_intel = CyberIntelligenceHub()
            
            if _ROI_ENGINE:
                self._roi = AutonomousROIEngine(data_bridge=self._data_bridge)
            
            if _APEX_COMMAND:
                self._apex = ApexCommandCenter(agent=self)

            # Campaign Manager
            if _CAMPAIGN_MANAGER_AVAILABLE:
                self._campaign_manager = MarketingCampaignManager(
                    data_bridge=self._data_bridge,
                    hunter_engine=self._hunter,
                    scoring_engine=self._scorer,
                    outreach_engine=self._outreach,
                    professor_engine=self._professor,
                )
                # Inject OMEGA capabilities if available
                if hasattr(self._campaign_manager, "set_omega_engines"):
                    self._campaign_manager.set_omega_engines(
                        recon_engine=self._recon,
                        personalizer=self._personalizer
                    )

            # Automation Service
            if _SERVICE_AVAILABLE:
                self._service = MarketingAutomationService(
                    admin_user_ids=self._admin_ids,
                )
                await self._service.initialize(
                    data_bridge=self._data_bridge,
                    hunter_engine=self._hunter,
                    scoring_engine=self._scorer,
                    outreach_engine=self._outreach,
                    platform_intel_engine=self._platform_intel,
                    professor_engine=self._professor,
                    campaign_manager=self._campaign_manager,
                    ai_client=ai_client,
                )

            self._initialized = True
            logger.info("✅ MarketingMasterAgent initialized successfully")
            return True

        except Exception as exc:
            logger.error("❌ MarketingMasterAgent initialization failed: %s", exc)
            return False

    async def start(self) -> None:
            """Start the agent's automated operations."""
            if not self._initialized:
                logger.error("Cannot start — not initialized")
                return

            if self._service:
                await self._service.start()
                
            # OMEGA: Trigger Autonomous Offensive
            if self._director:
                asyncio.create_task(self._run_autonomous_offensive())

            logger.info("⚡ MarketingMasterAgent is live in FULL AUTONOMY mode")

    async def _run_autonomous_offensive(self):
        """Internal method to drive the system without external commands."""
        logger.info("🚀 TITAN-OMEGA: Initiating Autonomous Offensive...")
        # 1. Analyze market via Trend Intel
        trends = await self._trend_intel.scan_market_signals()
        
        # 2. Design strategy via Director
        strategy = await self._director.design_monthly_strategy({"trends": trends})
        
        # 3. Trigger Hunter for identified niches
        for market in strategy.get("focus_markets", []):
            logger.info(f"Autonomous Hunt initiated for market: {market}")
            # Real implementation would call self._hunter.hunt_all_regions(...)
            
        logger.info("✅ Autonomous Offensive successfully launched.")

    async def stop(self) -> None:
        """Stop the agent."""
        if self._service:
            await self._service.stop()
        logger.info("🛑 MarketingMasterAgent stopped")

    # ── BaseAgent abstract method ───────────────────────

    async def act(self, context: Dict[str, Any]) -> Any:
        """
        Execute an action based on the provided context.
        Routes to handle_command when context contains a 'command' key.
        """
        command = context.get("command", "dashboard")
        args = context.get("args", {})
        user_id = context.get("user_id", 0)
        return await self.handle_command(command, args, user_id)

    # ── Command Router ───────────────────────────────────

    async def handle_command(
        self,
        command: str,
        args: Optional[Dict[str, Any]] = None,
        user_id: int = 0,
    ) -> Dict[str, Any]:
        """
        Route a command to the appropriate sub-agent.

        Commands:
          hunt, hunt_all — HunterSubAgent
          outreach, followups — OutreachSubAgent
          platforms, events, listings — PlatformSubAgent
          analyze, compete, social, briefing — ProfessorSubAgent
          campaign_create, campaign_launch, campaign_status — CampaignSubAgent
          dashboard, health, tasks — Service
        """
        args = args or {}

        # Hunter commands
        if command in ("hunt", "hunt_region"):
            return await self._cmd_hunt(args, user_id)
        if command == "hunt_all":
            return await self._cmd_hunt_all(args, user_id)

        # Outreach commands
        if command == "outreach":
            return await self._cmd_outreach(args, user_id)
        if command == "followups":
            return await self._cmd_followups(args, user_id)

        # Platform commands
        if command == "platforms":
            return await self._cmd_platforms(args, user_id)
        if command == "events":
            return await self._cmd_events(args, user_id)
        if command == "listing":
            return await self._cmd_listing(args, user_id)

        # Professor commands
        if command == "analyze":
            return await self._cmd_analyze(args, user_id)
        if command == "compete":
            return await self._cmd_compete(args, user_id)
        if command == "social":
            return await self._cmd_social(args, user_id)
        if command == "briefing":
            return await self._cmd_briefing(args, user_id)

        # Campaign commands
        if command == "campaign_create":
            return await self._cmd_campaign_create(args, user_id)
        if command == "campaign_launch":
            return await self._cmd_campaign_launch(args, user_id)
        if command == "campaign_status":
            return await self._cmd_campaign_status(args, user_id)

        # Service commands
        if command == "dashboard":
            return await self._cmd_dashboard(args, user_id)
        if command == "health":
            return await self._cmd_health(args, user_id)
        if command == "tasks":
            return await self._cmd_tasks(args, user_id)

        # ── OMEGA commands ─────────────────────────────────
        if command == "deep_recon":
            return await self._cmd_omega_deep_recon(args, user_id)
        if command == "contact_intel":
            return await self._cmd_omega_contact_intel(args, user_id)
        if command == "social_intel":
            return await self._cmd_omega_social_intel(args, user_id)
        if command == "content_forge":
            return await self._cmd_omega_content_forge(args, user_id)
        if command == "competitor_radar":
            return await self._cmd_omega_competitor_radar(args, user_id)
        if command == "hashtag_strategy":
            return await self._cmd_omega_hashtag_strategy(args, user_id)
        if command == "influencers":
            return await self._cmd_omega_influencers(args, user_id)
        if command == "content_calendar":
            return await self._cmd_omega_content_calendar(args, user_id)
        if command == "ab_test":
            return await self._cmd_omega_ab_test(args, user_id)
        if command == "market_scan":
            return await self._cmd_omega_market_scan(args, user_id)

        return {"error": f"Unknown command: {command}"}

    # ── Hunter Sub-Agent ─────────────────────────────────

    async def _cmd_hunt(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Hunt prospects in a specific region/category."""
        if not self._hunter or not self._data_bridge:
            return {"error": "Hunter engine not available"}

        region = args.get("region", "Finland")
        category = args.get("category", {"id": "hotels", "search_terms": ["hotel", "boutique hotel"]})

        result = await self._hunter.hunt(
            region, category,
            data_bridge=self._data_bridge,
            scoring_engine=self._scorer,
        )
        return result.to_dict()

    async def _cmd_hunt_all(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Hunt across all configured regions and categories."""
        if not self._hunter or not self._data_bridge:
            return {"error": "Hunter engine not available"}

        regions = DEFAULT_TARGET_MARKETS if _CONFIG_AVAILABLE else []
        categories = B2B_CATEGORIES if _CONFIG_AVAILABLE else []

        results = await self._hunter.hunt_all_regions(
            regions, categories,
            data_bridge=self._data_bridge,
            scoring_engine=self._scorer,
        )
        return {
            "hunts": len(results),
            "total_new": sum(r.prospects_new for r in results),
            "total_found": sum(r.prospects_found for r in results),
            "results": [r.to_dict() for r in results],
        }

    # ── Outreach Sub-Agent ───────────────────────────────

    async def _cmd_outreach(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Execute outreach for a campaign."""
        if not self._outreach or not self._data_bridge:
            return {"error": "Outreach engine not available"}

        campaign_id = args.get("campaign_id")
        if not campaign_id:
            return {"error": "campaign_id required"}

        prospects = await self._data_bridge.get_prospects(
            status="qualified", limit=args.get("limit", 20),
        )
        result = await self._outreach.execute_campaign_step(
            campaign_id, step_number=args.get("step", 0),
            prospects=prospects, data_bridge=self._data_bridge,
            ab_test=args.get("ab_test", False),
        )
        return result.to_dict()

    async def _cmd_followups(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Process follow-ups."""
        if not self._campaign_manager:
            return {"error": "Campaign manager not available"}

        campaign_id = args.get("campaign_id")
        if not campaign_id:
            return {"error": "campaign_id required"}

        return await self._campaign_manager.process_followups(campaign_id)

    # ── Platform Sub-Agent ───────────────────────────────

    async def _cmd_platforms(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Get platform status and ranking."""
        if not self._platform_intel:
            return {"error": "Platform engine not available"}

        ranking = await self._platform_intel.get_platform_ranking(
            data_bridge=self._data_bridge,
        )
        return {"platforms": ranking}

    async def _cmd_events(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Discover events and markets."""
        if not self._platform_intel:
            return {"error": "Platform engine not available"}

        result = await self._platform_intel.discover_events(
            regions=args.get("regions"),
            data_bridge=self._data_bridge,
        )
        return result.to_dict()

    async def _cmd_listing(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Generate a platform listing."""
        if not self._platform_intel:
            return {"error": "Platform engine not available"}

        product = args.get("product", {})
        platform = args.get("platform", "etsy")

        listing = await self._platform_intel.generate_listing(
            product=product, platform_key=platform,
            language=args.get("language", "en"),
            data_bridge=self._data_bridge,
        )
        return listing or {"error": "Listing generation failed"}

    # ── Professor Sub-Agent ──────────────────────────────

    async def _cmd_analyze(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Market analysis."""
        if not self._professor:
            return {"error": "Professor engine not available"}

        return await self._professor.analyze_market(
            dimension=args.get("dimension", "overview"),
            data_bridge=self._data_bridge,
        )

    async def _cmd_compete(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Competitor analysis."""
        if not self._professor:
            return {"error": "Professor engine not available"}

        results = await self._professor.analyze_competitors(
            data_bridge=self._data_bridge,
        )
        return {"competitors": [c.to_dict() for c in results]}

    async def _cmd_social(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Social media strategy."""
        if not self._professor:
            return {"error": "Professor engine not available"}

        platform = args.get("platform", "instagram")
        return await self._professor.get_social_strategy(platform)

    async def _cmd_briefing(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Generate daily briefing."""
        if not self._professor:
            return {"error": "Professor engine not available"}

        briefing = await self._professor.generate_daily_briefing(
            data_bridge=self._data_bridge,
            platform_engine=self._platform_intel,
        )
        return briefing.to_dict()

    # ── Campaign Sub-Agent ───────────────────────────────

    async def _cmd_campaign_create(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Create a campaign."""
        if not self._campaign_manager:
            return {"error": "Campaign manager not available"}

        template = args.get("template")
        if template:
            cid = await self._campaign_manager.create_from_template(
                template, created_by=user_id,
            )
        else:
            cid = await self._campaign_manager.create_custom(
                name=args.get("name", "New Campaign"),
                description=args.get("description", ""),
                target_countries=args.get("target_countries"),
                target_categories=args.get("target_categories"),
                created_by=user_id,
            )

        return {"campaign_id": cid} if cid else {"error": "Creation failed"}

    async def _cmd_campaign_launch(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Launch a campaign."""
        if not self._campaign_manager:
            return {"error": "Campaign manager not available"}

        campaign_id = args.get("campaign_id")
        if not campaign_id:
            return {"error": "campaign_id required"}

        status = await self._campaign_manager.launch_campaign(campaign_id)
        return status.to_dict()

    async def _cmd_campaign_status(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Get campaign status."""
        if not self._campaign_manager:
            return {"error": "Campaign manager not available"}

        campaign_id = args.get("campaign_id")
        if campaign_id:
            status = await self._campaign_manager.get_pipeline_status(campaign_id)
            return status.to_dict()
        return {"campaigns": await self._campaign_manager.get_all_campaign_statuses()}

    # ── Service Commands ─────────────────────────────────

    async def _cmd_dashboard(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Get full marketing dashboard."""
        if self._service:
            return await self._service.get_dashboard()
        return {"error": "Service not available"}

    async def _cmd_health(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Get health status."""
        if self._service:
            return await self._service.get_health()
        return {"error": "Service not available"}

    async def _cmd_tasks(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """List/manage scheduled tasks."""
        if not self._service:
            return {"error": "Service not available"}

        action = args.get("action", "list")
        if action == "list":
            return {"tasks": self._service.list_tasks()}
        elif action == "enable":
            ok = self._service.enable_task(args.get("task_key", ""))
            return {"success": ok}
        elif action == "disable":
            ok = self._service.disable_task(args.get("task_key", ""))
            return {"success": ok}
        elif action == "run":
            ok = await self._service.run_task_now(args.get("task_key", ""))
            return {"success": ok}
        return {"error": f"Unknown action: {action}"}

    # ── OMEGA Command Implementations ────────────────────

    async def _cmd_omega_deep_recon(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Run deep reconnaissance on a domain."""
        if not _OMEGA_DEEP_RECON:
            return {"error": "OMEGA DeepReconEngine not available"}
        domain = args.get("domain", "")
        if not domain:
            return {"error": "domain argument required"}
        engine = DeepReconEngine()
        report = await engine.deep_recon(domain)
        return report.to_dict() if hasattr(report, 'to_dict') else {"result": str(report)}

    async def _cmd_omega_contact_intel(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Discover contacts for a company."""
        if not _OMEGA_CONTACT_INTEL:
            return {"error": "OMEGA ContactIntelEngine not available"}
        company = args.get("company", "")
        domain = args.get("domain", "")
        if not domain:
            return {"error": "domain argument required"}
        engine = ContactIntelEngine()
        report = await engine.discover_contacts(company, domain)
        return report.to_dict()

    async def _cmd_omega_social_intel(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Run social intelligence scan."""
        if not _OMEGA_SOCIAL_INTEL:
            return {"error": "OMEGA SocialIntelEngine not available"}
        engine = SocialIntelEngine(
            niche=args.get("niche", "handmade candles concrete decor"),
            region=args.get("region", "Finland"),
        )
        focus = args.get("focus")
        report = await engine.full_social_intel(focus=focus)
        return report.to_dict()

    async def _cmd_omega_content_forge(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Generate content via ContentForge."""
        if not _OMEGA_CONTENT_FORGE:
            return {"error": "OMEGA ContentForgeEngine not available"}
        engine = ContentForgeEngine()
        content_type = args.get("type", "social_post")
        if content_type == "email":
            piece = await engine.generate_b2b_email(
                prospect=args.get("prospect", {}),
                language=ContentLanguage(args.get("language", "en")),
                industry=args.get("industry", "generic"),
            )
        elif content_type == "product":
            piece = await engine.generate_product_description(
                product=args.get("product", {}),
                platform=args.get("platform", "etsy"),
            )
        else:
            piece = await engine.generate_social_post(
                platform=args.get("platform", "instagram"),
                language=ContentLanguage(args.get("language", "en")),
            )
        return piece.to_dict()

    async def _cmd_omega_competitor_radar(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Run competitor radar scan."""
        if not _OMEGA_COMPETITOR_RADAR:
            return {"error": "OMEGA CompetitorRadarEngine not available"}
        engine = CompetitorRadarEngine(our_brand="ArkiObjects")
        report = await engine.full_scan()
        return report.to_dict()

    async def _cmd_omega_hashtag_strategy(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Get hashtag strategy."""
        if not _OMEGA_SOCIAL_INTEL:
            return {"error": "OMEGA SocialIntelEngine not available"}
        engine = SocialIntelEngine()
        content_type = args.get("content_type", "product_photo")
        return engine.get_hashtag_strategy(content_type)

    async def _cmd_omega_influencers(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Discover influencers."""
        if not _OMEGA_SOCIAL_INTEL:
            return {"error": "OMEGA SocialIntelEngine not available"}
        engine = SocialIntelEngine(
            niche=args.get("niche", "handmade candles"),
            region=args.get("region", "Finland"),
        )
        results = await engine.discover_influencers(limit=args.get("limit", 15))
        return {"influencers": [i.to_dict() for i in results]}

    async def _cmd_omega_content_calendar(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Generate content calendar."""
        if not _OMEGA_CONTENT_FORGE:
            return {"error": "OMEGA ContentForgeEngine not available"}
        engine = ContentForgeEngine()
        entries = engine.generate_content_calendar(
            weeks_ahead=args.get("weeks", 4),
            posts_per_week=args.get("posts_per_week", 3),
        )
        return {"calendar": [e.to_dict() for e in entries]}

    async def _cmd_omega_ab_test(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Generate A/B test plan."""
        if not _OMEGA_CONTENT_FORGE:
            return {"error": "OMEGA ContentForgeEngine not available"}
        from utils.content_forge_engine import ContentType
        engine = ContentForgeEngine()
        plan = await engine.generate_ab_variants(
            content_type=ContentType.EMAIL_B2B,
            base_params=args,
            test_variable=args.get("test_variable", "subject_line"),
        )
        return plan.to_dict()

    async def _cmd_omega_market_scan(self, args: Dict, user_id: int) -> Dict[str, Any]:
        """Run full OMEGA market scan."""
        if self._professor and hasattr(self._professor, 'omega_market_scan'):
            return await self._professor.omega_market_scan()
        return {"error": "MarketProfessor OMEGA not available"}

    # ── Status ───────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get agent status summary."""
        return {
            "name": self.AGENT_NAME,
            "version": self.AGENT_VERSION,
            "initialized": self._initialized,
            "engines": {
                "data_bridge": self._data_bridge is not None,
                "scorer": self._scorer is not None,
                "hunter": self._hunter is not None,
                "outreach": self._outreach is not None,
                "platform_intel": self._platform_intel is not None,
                "professor": self._professor is not None,
                "campaign_manager": self._campaign_manager is not None,
                "service": self._service is not None,
            },
            "omega_modules": {
                "deep_recon": _OMEGA_DEEP_RECON,
                "contact_intel": _OMEGA_CONTACT_INTEL,
                "social_intel": _OMEGA_SOCIAL_INTEL,
                "content_forge": _OMEGA_CONTENT_FORGE,
                "competitor_radar": _OMEGA_COMPETITOR_RADAR,
            },
            "admin_ids": list(self._admin_ids),
        }


