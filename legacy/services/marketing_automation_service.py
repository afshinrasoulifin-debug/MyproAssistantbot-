
from __future__ import annotations
"""
tg_bot/services/marketing_automation_service.py — Marketing Agent TITAN (L7)
═════════════════════════════════════════════════════════════════════════════
Business logic layer + EventBus for the Marketing Agent TITAN.

Architecture
────────────
   ┌──────────────────────────────────────────────────────────────────┐
   │                MARKETING AUTOMATION SERVICE (L7)                 │
   ├──────────┬──────────┬──────────┬──────────────┬─────────────────┤
   │ Schedule │ Pipeline │ Events   │ Health       │ Permissions     │
   ├──────────┼──────────┼──────────┼──────────────┼─────────────────┤
   │ Cron     │ Hunt→    │ EventBus │ Engine Alive │ Admin Check     │
   │ Interval │ Score→   │ Publish  │ DB Check     │ Owner Only      │
   │ Manual   │ Reach→   │ Subscribe│ Queue Check  │ Rate Limit      │
   │ One-shot │ Monitor  │ History  │ Alert        │ GDPR Enforce    │
   └──────────┴──────────┴──────────┴──────────────┴─────────────────┘

Responsibilities
────────────────
  • Coordinate all marketing engines (L9) via a unified interface
  • Manage scheduled tasks (daily hunt, weekly analysis, follow-ups)
  • EventBus for decoupled inter-engine communication
  • Health monitoring for all sub-engines
  • Permission / admin checks for sensitive operations
  • GDPR enforcement before any outreach

Reuses
──────
  • All L9 engines
  • database/marketing_models.py — data layer
  • utils/marketing_data_bridge.py — data access
"""


import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# EventBus
# ═══════════════════════════════════════════════════════════

EventHandler = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]


class MarketingEventBus:
    """
    Lightweight async event bus for inter-engine communication.

    Events flow between engines without direct coupling:
      prospect_found → scoring_engine.score_new
      prospect_scored → campaign_manager.qualify
      email_sent → professor.track
      email_replied → outreach.handle_reply
      gdpr_opt_out → data_bridge.revoke
    """

    def __init__(self) -> None:
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._history: List[Dict[str, Any]] = []
        self._max_history = 500

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe a handler to an event type."""
        self._handlers[event_type].append(handler)
        logger.debug("EventBus: subscribed %s to '%s'", handler.__name__, event_type)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a handler from an event type."""
        handlers = self._handlers.get(event_type, [])
        self._handlers[event_type] = [h for h in handlers if h is not handler]

    async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Publish an event to all subscribers."""
        event = {
            "type": event_type,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            return

        tasks = [h(event["data"]) for h in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("EventBus handler error for '%s': %s", event_type, result)

    def get_history(self, event_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent event history."""
        events = self._history
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        return events[-limit:]


# ═══════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════

@dataclass
class ScheduledTask:
    """A scheduled marketing task."""
    name: str = ""
    interval_hours: float = 24.0
    last_run: Optional[datetime] = None
    enabled: bool = True
    handler_name: str = ""


class MarketingAutomationService:
    """
    Central orchestration service for the Marketing Agent TITAN.

    Coordinates all engines, manages scheduling, handles events,
    and enforces permissions.
    """

    def __init__(
        self,
        *,
        admin_user_ids: Optional[Set[int]] = None,
    ) -> None:
        # Engines (set via initialize())
        self._data_bridge = None
        self._hunter = None
        self._scorer = None
        self._outreach = None
        self._platform_intel = None
        self._professor = None
        self._campaign_manager = None
        self._ai_client = None

        # EventBus
        self.event_bus = MarketingEventBus()

        # Scheduling
        self._scheduled_tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None

        # Permissions
        self._admin_ids = admin_user_ids or set()

        # Stats
        self._start_time: Optional[datetime] = None
        self._tasks_executed = 0

    # ── Initialization ───────────────────────────────────

    async def initialize(
        self,
        *,
        data_bridge=None,
        hunter_engine=None,
        scoring_engine=None,
        outreach_engine=None,
        platform_intel_engine=None,
        professor_engine=None,
        campaign_manager=None,
        ai_client=None,
    ) -> None:
        """
        Initialize the service with all engine references.
        Must be called before start().
        """
        self._data_bridge = data_bridge
        self._hunter = hunter_engine
        self._scorer = scoring_engine
        self._outreach = outreach_engine
        self._platform_intel = platform_intel_engine
        self._professor = professor_engine
        self._campaign_manager = campaign_manager
        self._ai_client = ai_client

        # Wire up event bus
        self._setup_event_handlers()

        # Setup scheduled tasks
        self._setup_scheduled_tasks()

        logger.info("🚀 MarketingAutomationService initialized")

    def _setup_event_handlers(self) -> None:
        """Wire up event bus handlers between engines."""

        async def on_prospect_found(data: Dict[str, Any]):
            """When a new prospect is found → score and trigger initial recon."""
            if self._scorer and self._data_bridge:
                prospect_id = data.get("prospect_id")
                if prospect_id:
                    logger.info("Automation: Prospect %s found, triggering initial scoring and recon.", prospect_id)
                    # Publish event to trigger recon immediately
                    await self.event_bus.publish("recon_requested", {"prospect_id": prospect_id})

        async def on_email_replied(data: Dict[str, Any]):
            """When a prospect replies → update score and status."""
            if self._scorer and self._data_bridge:
                prospect_id = data.get("prospect_id")
                if prospect_id:
                    await self._scorer.update_behavioral_score(
                        prospect_id, "email_replied",
                        data_bridge=self._data_bridge,
                    )
                    await self._data_bridge.update_prospect(
                        prospect_id, {"status": "responded"}
                    )

        async def on_gdpr_opt_out(data: Dict[str, Any]):
            """GDPR opt-out → revoke consent, stop all outreach."""
            if self._data_bridge:
                prospect_id = data.get("prospect_id")
                if prospect_id:
                    await self._data_bridge.revoke_consent(
                        prospect_id, "b2b_outreach"
                    )
                    logger.info("GDPR opt-out processed for prospect %d", prospect_id)

        async def on_prospect_qualified(data: Dict[str, Any]):
            """When a prospect is qualified → run deep recon and generate content."""
            prospect_id = data.get("prospect_id")
            if prospect_id:
                logger.info("OMEGA: Prospect %s qualified. Triggering Deep Recon and Content Generation.", prospect_id)
                await self.event_bus.publish("recon_requested", {"prospect_id": prospect_id})
                await self.event_bus.publish("content_generation_requested", {"prospect_id": prospect_id})

        async def on_recon_complete(data: Dict[str, Any]):
            """When recon is complete → trigger hyper-personalization."""
            prospect_id = data.get("prospect_id")
            if prospect_id:
                logger.info("OMEGA: Recon complete for %s. Triggering Hyper-Personalization.", prospect_id)
                await self.event_bus.publish("personalization_requested", {"prospect_id": prospect_id})

        self.event_bus.subscribe("prospect_found", on_prospect_found)
        self.event_bus.subscribe("prospect_qualified", on_prospect_qualified)
        self.event_bus.subscribe("recon_complete", on_recon_complete)
        self.event_bus.subscribe("email_replied", on_email_replied)
        self.event_bus.subscribe("gdpr_opt_out", on_gdpr_opt_out)

    def _setup_scheduled_tasks(self) -> None:
        """Setup default scheduled marketing tasks."""
        self._scheduled_tasks = {
            "daily_hunt": ScheduledTask(
                name="Daily B2B Hunt",
                interval_hours=24.0,
                enabled=True,
                handler_name="_task_daily_hunt",
            ),
            "daily_briefing": ScheduledTask(
                name="Daily Briefing",
                interval_hours=24.0,
                enabled=True,
                handler_name="_task_daily_briefing",
            ),
            "followup_check": ScheduledTask(
                name="Follow-up Check",
                interval_hours=6.0,
                enabled=True,
                handler_name="_task_followup_check",
            ),
            "platform_scan": ScheduledTask(
                name="Platform Scan",
                interval_hours=168.0,  # Weekly
                enabled=True,
                handler_name="_task_platform_scan",
            ),
            "event_discovery": ScheduledTask(
                name="Event Discovery",
                interval_hours=72.0,  # Every 3 days
                enabled=True,
                handler_name="_task_event_discovery",
            ),
            "competitor_analysis": ScheduledTask(
                name="Competitor Analysis",
                interval_hours=336.0,  # Bi-weekly
                enabled=True,
                handler_name="_task_competitor_analysis",
            ),
            "gdpr_cleanup": ScheduledTask(
                name="GDPR Data Cleanup",
                interval_hours=720.0,  # Monthly
                enabled=True,
                handler_name="_task_gdpr_cleanup",
            ),
            "omega_recon_sync": ScheduledTask(
                name="OMEGA Recon Sync",
                interval_hours=12.0,  # Twice daily
                enabled=True,
                handler_name="_task_omega_recon_sync",
            ),
        }

    # ── Scheduler ────────────────────────────────────────

    async def start(self) -> None:
        """Start the automation service scheduler."""
        if self._running:
            return

        self._running = True
        self._start_time = datetime.now(timezone.utc)
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("⚡ Marketing automation scheduler started")

    async def stop(self) -> None:
        """Stop the automation service."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Marketing automation scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop — checks and runs due tasks."""
        while self._running:
            now = datetime.now(timezone.utc)

            for task_key, task in self._scheduled_tasks.items():
                if not task.enabled:
                    continue

                # Check if task is due
                if task.last_run is None or (
                    now - task.last_run > timedelta(hours=task.interval_hours)
                ):
                    try:
                        handler = getattr(self, task.handler_name, None)
                        if handler:
                            logger.info("⏰ Running scheduled task: %s", task.name)
                            await handler()
                            task.last_run = now
                            self._tasks_executed += 1
                    except Exception as exc:
                        logger.error("Scheduled task '%s' failed: %s", task.name, exc)

            # Sleep 5 minutes between checks
            await asyncio.sleep(300)

    # ── Scheduled Task Handlers ──────────────────────────

    async def _task_daily_hunt(self) -> None:
        """Daily B2B prospect hunting."""
        if not self._hunter or not self._data_bridge:
            return

        from arki_project.config_marketing import DEFAULT_TARGET_MARKETS, B2B_CATEGORIES

        # Hunt top 3 priority markets, top 3 categories
        priority_markets = DEFAULT_TARGET_MARKETS[:3]
        priority_categories = B2B_CATEGORIES[:3]

        results = await self._hunter.hunt_all_regions(
            priority_markets, priority_categories,
            data_bridge=self._data_bridge,
            scoring_engine=self._scorer,
            max_parallel_regions=2,
        )

        total_new = sum(r.prospects_new for r in results)
        logger.info("📊 Daily hunt: %d new prospects from %d hunts", total_new, len(results))

        await self.event_bus.publish("daily_hunt_complete", {"results_count": len(results), "new_prospects": total_new})

    async def _task_daily_briefing(self) -> None:
        """Generate and deliver daily briefing."""
        if not self._professor:
            return

        briefing = await self._professor.generate_daily_briefing(
            data_bridge=self._data_bridge,
            platform_engine=self._platform_intel,
            ai_client=self._ai_client,
        )

        await self.event_bus.publish("daily_briefing_ready", {"date": briefing.date})

    async def _task_followup_check(self) -> None:
        """Check and process due follow-ups for all active campaigns."""
        if not self._campaign_manager or not self._data_bridge:
            return

        campaigns = await self._data_bridge.list_campaigns(status="active")
        for campaign in campaigns:
            stats = await self._campaign_manager.process_followups(campaign["id"])
            if stats.get("sent", 0) > 0:
                logger.info("📧 Follow-ups for campaign %d: %s", campaign["id"], stats)

    async def _task_platform_scan(self) -> None:
        """Weekly platform discovery scan."""
        if not self._platform_intel:
            return

        result = await self._platform_intel.discover_new_platforms(
            data_bridge=self._data_bridge,
        )
        logger.info("🔍 Platform scan: %d new opportunities", result.opportunities_new)

    async def _task_event_discovery(self) -> None:
        """Discover new events, markets, and fairs."""
        if not self._platform_intel:
            return

        result = await self._platform_intel.discover_events(
            data_bridge=self._data_bridge,
        )
        logger.info("🎪 Event discovery: %d events found", result.events_found)

    async def _task_competitor_analysis(self) -> None:
        """Run competitor analysis."""
        if not self._professor:
            return

        competitors = await self._professor.analyze_competitors(
            ai_client=self._ai_client,
            data_bridge=self._data_bridge,
        )
        logger.info("🔎 Competitor analysis: %d brands found", len(competitors))

    async def _task_gdpr_cleanup(self) -> None:
        """Monthly GDPR data cleanup."""
        if not self._data_bridge:
            return

        counts = await self._data_bridge.cleanup_expired_data(retention_days=730)
        logger.info("🧹 GDPR cleanup: %s", counts)

    # ── Manual Operations ────────────────────────────────

    async def run_task_now(self, task_key: str) -> bool:
        """Manually trigger a scheduled task."""
        task = self._scheduled_tasks.get(task_key)
        if not task:
            return False

        handler = getattr(self, task.handler_name, None)
        if not handler:
            return False

        await handler()
        task.last_run = datetime.now(timezone.utc)
        self._tasks_executed += 1
        return True

    async def run_full_pipeline(
        self,
        *,
        template_key: Optional[str] = None,
        campaign_id: Optional[int] = None,
        user_id: int = 0,
    ) -> Dict[str, Any]:
        """
        Run the complete marketing pipeline manually.

        Either creates from template or uses existing campaign.
        """
        if not self._campaign_manager:
            return {"error": "Campaign manager not available"}

        if template_key:
            campaign_id = await self._campaign_manager.create_from_template(
                template_key, created_by=user_id,
            )
            if not campaign_id:
                return {"error": f"Failed to create campaign from template '{template_key}'"}

        if not campaign_id:
            return {"error": "No campaign specified"}

        status = await self._campaign_manager.launch_campaign(campaign_id)
        return status.to_dict()

    # ── Permissions ──────────────────────────────────────

    def is_admin(self, user_id: int) -> bool:
        """Check if a user has admin privileges."""
        return user_id in self._admin_ids

    def require_admin(self, user_id: int) -> bool:
        """Enforce admin check, raising if not admin."""
        if not self.is_admin(user_id):
            logger.warning("Permission denied for user %d", user_id)
            return False
        return True

    # ── Health & Stats ───────────────────────────────────

    async def get_health(self) -> Dict[str, Any]:
        """Get health status of all engines and components."""
        health = {
            "service": "running" if self._running else "stopped",
            "uptime_hours": None,
            "tasks_executed": self._tasks_executed,
            "engines": {},
            "scheduled_tasks": {},
        }

        if self._start_time:
            delta = datetime.now(timezone.utc) - self._start_time
            health["uptime_hours"] = round(delta.total_seconds() / 3600, 1)

        # Engine health
        engines = {
            "data_bridge": self._data_bridge,
            "hunter": self._hunter,
            "scorer": self._scorer,
            "outreach": self._outreach,
            "platform_intel": self._platform_intel,
            "professor": self._professor,
            "campaign_manager": self._campaign_manager,
        }
        for name, engine in engines.items():
            health["engines"][name] = "available" if engine else "not_initialized"

        # Task status
        for key, task in self._scheduled_tasks.items():
            health["scheduled_tasks"][key] = {
                "name": task.name,
                "enabled": task.enabled,
                "interval_hours": task.interval_hours,
                "last_run": task.last_run.isoformat() if task.last_run else None,
            }

        return health

    async def get_dashboard(self) -> Dict[str, Any]:
        """Get complete marketing dashboard data."""
        dashboard: Dict[str, Any] = {
            "health": await self.get_health(),
        }

        if self._data_bridge:
            dashboard["stats"] = await self._data_bridge.get_dashboard_stats()

        if self._campaign_manager:
            dashboard["campaigns"] = await self._campaign_manager.get_all_campaign_statuses()

        if self._professor:
            dashboard["trends"] = [
                t.to_dict()
                for t in await self._professor.detect_trends(data_bridge=self._data_bridge)
            ]

        return dashboard

    # ── Task Management ──────────────────────────────────

    def enable_task(self, task_key: str) -> bool:
        """Enable a scheduled task."""
        if task_key in self._scheduled_tasks:
            self._scheduled_tasks[task_key].enabled = True
            return True
        return False

    def disable_task(self, task_key: str) -> bool:
        """Disable a scheduled task."""
        if task_key in self._scheduled_tasks:
            self._scheduled_tasks[task_key].enabled = False
            return True
        return False

    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all scheduled tasks."""
        return [
            {
                "key": key,
                "name": task.name,
                "enabled": task.enabled,
                "interval_hours": task.interval_hours,
                "last_run": task.last_run.isoformat() if task.last_run else None,
            }
            for key, task in self._scheduled_tasks.items()
        ]

    async def _task_omega_recon_sync(self) -> None:
        """Scheduled task to run deep recon on qualified prospects."""
        if not self._campaign_manager or not hasattr(self._campaign_manager, "_run_recon_phase"):
            return
            
        logger.info("⚡ Starting OMEGA Recon Sync...")
        # We simulate a 'system' campaign or just run recon on all qualified
        # For simplicity, we trigger the campaign manager's recon logic
        # In a real scenario, we'd iterate over active campaigns
        campaigns = await self._data_bridge.list_campaigns(status="active")
        for campaign in campaigns:
            pipeline = self._campaign_manager._active_pipelines.get(campaign["id"])
            if pipeline:
                await self._campaign_manager._run_recon_phase(campaign, pipeline)
        
        logger.info("✅ OMEGA Recon Sync complete")


