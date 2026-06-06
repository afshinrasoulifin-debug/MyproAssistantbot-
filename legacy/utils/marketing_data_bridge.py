
from __future__ import annotations
"""
tg_bot/utils/marketing_data_bridge.py — Marketing Data Bridge + GDPR Layer (L5)
═════════════════════════════════════════════════════════════════════════════════
Unified data access for all marketing tables with built-in GDPR compliance.

Provides:
  • CRUD for all 9 marketing tables
  • Query builders for common patterns
  • Aggregation helpers for reporting
  • GDPR consent tracking and enforcement
  • Data retention and cleanup
  • Deduplication via fingerprinting

All database operations go through this bridge — engines never touch
the session directly.
"""


import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select, update, and_, or_, desc


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Fingerprinting (deduplication)
# ═══════════════════════════════════════════════════════════

def prospect_fingerprint(name: str, city: str, country: str) -> str:
    """Generate a stable dedup fingerprint for a prospect."""
    normalized = f"{name.lower().strip()}|{city.lower().strip()}|{country.lower().strip()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def opportunity_fingerprint(name: str, country: str, event_start: Optional[str] = None) -> str:
    """Generate a stable dedup fingerprint for an opportunity."""
    parts = f"{name.lower().strip()}|{country.lower().strip()}"
    if event_start:
        parts += f"|{event_start}"
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()[:32]


# ═══════════════════════════════════════════════════════════
# Data Bridge Class
# ═══════════════════════════════════════════════════════════

class MarketingDataBridge:
    """Unified data access layer for the Marketing Agent TITAN."""

    def __init__(self) -> None:
        self._stats = {
            "prospects_created": 0,
            "emails_sent": 0,
            "events_logged": 0,
        }

    # ──────────────────────────────────────────────────────
    # Prospects
    # ──────────────────────────────────────────────────────

    async def create_prospect(self, data: Dict[str, Any]) -> Optional[int]:
        """
        Insert a new prospect.  Returns the new ID, or None if duplicate.
        Automatically generates fingerprint and checks for dups.
        """
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import Prospect

        fp = prospect_fingerprint(
            data.get("business_name", ""),
            data.get("city", ""),
            data.get("country", ""),
        )

        try:
            async with get_session() as session:
                # Dedup check
                existing = await session.execute(
                    select(Prospect.id).where(Prospect.fingerprint == fp)
                )
                if existing.scalar_one_or_none() is not None:
                    logger.debug("Duplicate prospect skipped: %s", data.get("business_name"))
                    return None

                prospect = Prospect(
                    business_name=data["business_name"],
                    business_type=data.get("business_type", "unknown"),
                    website=data.get("website"),
                    email=data.get("email"),
                    phone=data.get("phone"),
                    contact_person=data.get("contact_person"),
                    contact_role=data.get("contact_role"),
                    country=data.get("country", ""),
                    city=data.get("city"),
                    region=data.get("region"),
                    latitude=data.get("latitude"),
                    longitude=data.get("longitude"),
                    score=data.get("score", 0.0),
                    score_factors=json.dumps(data.get("score_factors", {}), ensure_ascii=False),
                    status="discovered",
                    source=data.get("source", "b2b_hunter"),
                    source_url=data.get("source_url"),
                    source_query=data.get("source_query"),
                    language=data.get("language", "en"),
                    timezone=data.get("timezone"),
                    notes=data.get("notes"),
                    tags=json.dumps(data.get("tags", []), ensure_ascii=False),
                    extra_data=json.dumps(data.get("extra_data", {}), ensure_ascii=False),
                    gdpr_basis=data.get("gdpr_basis", "legitimate_interest"),
                    fingerprint=fp,
                )
                session.add(prospect)
                await session.flush()
                pid = prospect.id
                self._stats["prospects_created"] += 1
                return pid
        except Exception as exc:
            logger.error("create_prospect error: %s", exc)
            return None

    async def get_prospects(
        self,
        *,
        status: Optional[str] = None,
        country: Optional[str] = None,
        business_type: Optional[str] = None,
        min_score: float = 0.0,
        limit: int = 50,
        offset: int = 0,
        order_by_score: bool = True,
        exclude_opted_out: bool = True,
    ) -> List[Dict[str, Any]]:
        """Query prospects with flexible filters."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import Prospect

        try:
            async with get_session() as session:
                stmt = select(Prospect)
                if status:
                    stmt = stmt.where(Prospect.status == status)
                if country:
                    stmt = stmt.where(Prospect.country == country)
                if business_type:
                    stmt = stmt.where(Prospect.business_type == business_type)
                if min_score > 0:
                    stmt = stmt.where(Prospect.score >= min_score)
                if exclude_opted_out:
                    stmt = stmt.where(Prospect.opted_out == False)

                if order_by_score:
                    stmt = stmt.order_by(desc(Prospect.score))
                else:
                    stmt = stmt.order_by(desc(Prospect.discovered_at))

                stmt = stmt.offset(offset).limit(limit)
                result = await session.execute(stmt)
                prospects = result.scalars().all()

                return [self._prospect_to_dict(p) for p in prospects]
        except Exception as exc:
            logger.error("get_prospects error: %s", exc)
            return []

    async def update_prospect(self, prospect_id: int, updates: Dict[str, Any]) -> bool:
        """Update a prospect's fields."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import Prospect

        try:
            async with get_session() as session:
                await session.execute(
                    update(Prospect)
                    .where(Prospect.id == prospect_id)
                    .values(**updates)
                )
                return True
        except Exception as exc:
            logger.error("update_prospect error: %s", exc)
            return False

    async def count_prospects(self, **filters) -> int:
        """Count prospects matching filters."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import Prospect

        try:
            async with get_session() as session:
                stmt = select(func.count()).select_from(Prospect)
                if "status" in filters:
                    stmt = stmt.where(Prospect.status == filters["status"])
                if "country" in filters:
                    stmt = stmt.where(Prospect.country == filters["country"])
                result = await session.execute(stmt)
                return result.scalar() or 0
        except Exception:
            return 0

    # ──────────────────────────────────────────────────────
    # Outreach Campaigns
    # ──────────────────────────────────────────────────────

    async def create_campaign(self, data: Dict[str, Any]) -> Optional[int]:
        """Create a new outreach campaign."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import OutreachCampaign

        try:
            async with get_session() as session:
                campaign = OutreachCampaign(
                    name=data["name"],
                    description=data.get("description"),
                    target_countries=json.dumps(data.get("target_countries", []), ensure_ascii=False),
                    target_categories=json.dumps(data.get("target_categories", []), ensure_ascii=False),
                    min_score=data.get("min_score", 0.0),
                    status="draft",
                    created_by=data.get("created_by", 0),
                )
                session.add(campaign)
                await session.flush()
                return campaign.id
        except Exception as exc:
            logger.error("create_campaign error: %s", exc)
            return None

    async def get_campaign(self, campaign_id: int) -> Optional[Dict[str, Any]]:
        """Get a single campaign by ID."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import OutreachCampaign

        try:
            async with get_session() as session:
                result = await session.execute(
                    select(OutreachCampaign).where(OutreachCampaign.id == campaign_id)
                )
                c = result.scalar_one_or_none()
                return self._campaign_to_dict(c) if c else None
        except Exception as exc:
            logger.error("get_campaign error: %s", exc)
            return None

    async def list_campaigns(self, status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """List campaigns with optional status filter."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import OutreachCampaign

        try:
            async with get_session() as session:
                stmt = select(OutreachCampaign).order_by(desc(OutreachCampaign.created_at)).limit(limit)
                if status:
                    stmt = stmt.where(OutreachCampaign.status == status)
                result = await session.execute(stmt)
                return [self._campaign_to_dict(c) for c in result.scalars().all()]
        except Exception:
            return []

    async def update_campaign(self, campaign_id: int, updates: Dict[str, Any]) -> bool:
        """Update campaign fields."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import OutreachCampaign

        try:
            async with get_session() as session:
                await session.execute(
                    update(OutreachCampaign)
                    .where(OutreachCampaign.id == campaign_id)
                    .values(**updates)
                )
                return True
        except Exception as exc:
            logger.error("update_campaign error: %s", exc)
            return False

    async def get_prospect(self, prospect_id: int) -> Optional[Dict[str, Any]]:
        """Get a single prospect by ID."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import Prospect

        try:
            async with get_session() as session:
                result = await session.execute(
                    select(Prospect).where(Prospect.id == prospect_id)
                )
                p = result.scalar_one_or_none()
                return self._prospect_to_dict(p) if p else None
        except Exception as exc:
            logger.error("get_prospect error: %s", exc)
            return None

    async def log_event(
        self,
        event_type: str,
        prospect_id: Optional[int] = None,
        campaign_id: Optional[int] = None,
        email_id: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        outcome: str = "info",
    ) -> bool:
        """Log a marketing event."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import MarketingEvent

        try:
            async with get_session() as session:
                event = MarketingEvent(
                    event_type=event_type,
                    prospect_id=prospect_id,
                    campaign_id=campaign_id,
                    email_id=email_id,
                    data=json.dumps(data or {}, ensure_ascii=False),
                    outcome=outcome,
                )
                session.add(event)
                await session.flush()
                self._stats["events_logged"] += 1
                return True
        except Exception as exc:
            logger.error("log_event error: %s", exc)
            return False

    async def queue_email(self, data: Dict[str, Any]) -> Optional[int]:
        """Queue an email for sending."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import OutreachEmail

        try:
            async with get_session() as session:
                email = OutreachEmail(
                    campaign_id=data["campaign_id"],
                    prospect_id=data["prospect_id"],
                    sequence_step=data.get("sequence_step", 0),
                    to_email=data["to_email"],
                    subject=data["subject"],
                    body_html=data["body_html"],
                    language=data.get("language", "en"),
                    variant_label=data.get("variant_label"),
                    status="queued",
                )
                session.add(email)
                await session.flush()
                return email.id
        except Exception as exc:
            logger.error("queue_email error: %s", exc)
            return None

    async def update_email_status(
        self,
        email_id: int,
        status: str,
        sent_at: Optional[datetime] = None,
        provider: Optional[str] = None,
        error: Optional[str] = None,
    ) -> bool:
        """Update the status of a queued email."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import OutreachEmail

        try:
            async with get_session() as session:
                values = {"status": status}
                if sent_at:
                    values["sent_at"] = sent_at
                if provider:
                    values["provider"] = provider
                if error:
                    values["error_message"] = error
                
                await session.execute(
                    update(OutreachEmail)
                    .where(OutreachEmail.id == email_id)
                    .values(**values)
                )
                if status == "sent":
                    self._stats["emails_sent"] += 1
                return True
        except Exception as exc:
            logger.error("update_email_status error: %s", exc)
            return False

    # ──────────────────────────────────────────────────────
    # Outreach Sequences
    # ──────────────────────────────────────────────────────

    async def create_sequence_step(self, data: Dict[str, Any]) -> Optional[int]:
        """Add a step to a campaign's email sequence."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import OutreachSequence

        try:
            async with get_session() as session:
                step = OutreachSequence(
                    campaign_id=data["campaign_id"],
                    step_number=data["step_number"],
                    delay_days=data.get("delay_days", 0),
                    subject_template=data["subject_template"],
                    body_template=data["body_template"],
                    language=data.get("language", "en"),
                    attach_catalog=data.get("attach_catalog", False),
                    variant_label=data.get("variant_label"),
                )
                session.add(step)
                await session.flush()
                return step.id
        except Exception as exc:
            logger.error("create_sequence_step error: %s", exc)
            return None

    async def get_sequence_steps(self, campaign_id: int) -> List[Dict[str, Any]]:
        """Get all sequence steps for a campaign."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import OutreachSequence

        try:
            async with get_session() as session:
                result = await session.execute(
                    select(OutreachSequence)
                    .where(OutreachSequence.campaign_id == campaign_id)
                    .order_by(OutreachSequence.step_number)
                )
                steps = result.scalars().all()
                return [
                    {
                        "id": s.id,
                        "campaign_id": s.campaign_id,
                        "step_number": s.step_number,
                        "delay_days": s.delay_days,
                        "subject_template": s.subject_template,
                        "body_template": s.body_template,
                        "language": s.language,
                        "attach_catalog": s.attach_catalog,
                        "variant_label": s.variant_label,
                    }
                    for s in steps
                ]
        except Exception:
            return []

    # ──────────────────────────────────────────────────────
    # Outreach Emails
    # ──────────────────────────────────────────────────────

    async def queue_email(self, data: Dict[str, Any]) -> Optional[int]:
        """Queue an email for sending."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import OutreachEmail

        try:
            async with get_session() as session:
                email = OutreachEmail(
                    campaign_id=data["campaign_id"],
                    prospect_id=data["prospect_id"],
                    sequence_step=data.get("sequence_step", 0),
                    to_email=data["to_email"],
                    subject=data["subject"],
                    body_html=data["body_html"],
                    language=data.get("language", "en"),
                    variant_label=data.get("variant_label"),
                    status="queued",
                )
                session.add(email)
                await session.flush()
                return email.id
        except Exception as exc:
            logger.error("queue_email error: %s", exc)
            return None

    async def get_queued_emails(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get queued emails ready to send."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import OutreachEmail

        try:
            async with get_session() as session:
                result = await session.execute(
                    select(OutreachEmail)
                    .where(OutreachEmail.status_code == "queued")
                    .order_by(OutreachEmail.created_at)
                    .limit(limit)
                )
                emails = result.scalars().all()
                return [self._email_to_dict(e) for e in emails]
        except Exception:
            return []

    async def update_email_status(
        self,
        email_id: int,
        status: str,
        **extra_fields,
    ) -> bool:
        """Update an email's delivery status."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import OutreachEmail

        updates = {"status": status, **extra_fields}
        try:
            async with get_session() as session:
                await session.execute(
                    update(OutreachEmail).where(OutreachEmail.id == email_id).values(**updates)
                )
                return True
        except Exception as exc:
            logger.error("update_email_status error: %s", exc)
            return False

    async def get_campaign_email_stats(self, campaign_id: int) -> Dict[str, int]:
        """Get aggregated email stats for a campaign."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import OutreachEmail

        try:
            async with get_session() as session:
                result = await session.execute(
                    select(OutreachEmail.status_code, func.count())
                    .where(OutreachEmail.campaign_id == campaign_id)
                    .group_by(OutreachEmail.status_code)
                )
                return {row[0]: row[1] for row in result.all()}
        except Exception:
            return {}

    # ──────────────────────────────────────────────────────
    # Platform Listings
    # ──────────────────────────────────────────────────────

    async def create_listing(self, data: Dict[str, Any]) -> Optional[int]:
        """Create a new platform listing."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import PlatformListing

        try:
            async with get_session() as session:
                listing = PlatformListing(
                    platform_key=data["platform_key"],
                    product_name=data["product_name"],
                    title=data["title"],
                    description=data["description"],
                    tags=json.dumps(data.get("tags", []), ensure_ascii=False),
                    price_eur=data["price_eur"],
                    currency=data.get("currency", "EUR"),
                    images=json.dumps(data.get("images", []), ensure_ascii=False),
                    language=data.get("language", "en"),
                    status="draft",
                )
                session.add(listing)
                await session.flush()
                return listing.id
        except Exception as exc:
            logger.error("create_listing error: %s", exc)
            return None

    async def get_listings(
        self,
        platform_key: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query platform listings."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import PlatformListing

        try:
            async with get_session() as session:
                stmt = select(PlatformListing).order_by(desc(PlatformListing.updated_at)).limit(limit)
                if platform_key:
                    stmt = stmt.where(PlatformListing.platform_key == platform_key)
                if status:
                    stmt = stmt.where(PlatformListing.status_code == status)
                result = await session.execute(stmt)
                return [
                    {
                        "id": l.id, "platform_key": l.platform_key,
                        "product_name": l.product_name, "title": l.title,
                        "price_eur": l.price_eur, "status": l.status_code,
                        "views": l.views, "favorites": l.favorites,
                        "sales": l.sales, "revenue_eur": l.revenue_eur,
                    }
                    for l in result.scalars().all()
                ]
        except Exception:
            return []

    # ──────────────────────────────────────────────────────
    # Platform Opportunities
    # ──────────────────────────────────────────────────────

    async def create_opportunity(self, data: Dict[str, Any]) -> Optional[int]:
        """Store a discovered platform or event opportunity."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import PlatformOpportunity

        fp = opportunity_fingerprint(
            data.get("name", ""),
            data.get("country", ""),
            data.get("event_start"),
        )

        try:
            async with get_session() as session:
                existing = await session.execute(
                    select(PlatformOpportunity.id).where(PlatformOpportunity.fingerprint == fp)
                )
                if existing.scalar_one_or_none() is not None:
                    return None  # duplicate

                opp = PlatformOpportunity(
                    opportunity_type=data.get("opportunity_type", "online_platform"),
                    name=data["name"],
                    description=data.get("description"),
                    url=data.get("url"),
                    country=data.get("country"),
                    city=data.get("city"),
                    event_start=data.get("event_start"),
                    event_end=data.get("event_end"),
                    application_deadline=data.get("application_deadline"),
                    relevance_score=data.get("relevance_score", 0.0),
                    estimated_cost_eur=data.get("estimated_cost_eur"),
                    notes=data.get("notes"),
                    source=data.get("source", "platform_scout"),
                    fingerprint=fp,
                )
                session.add(opp)
                await session.flush()
                return opp.id
        except Exception as exc:
            logger.error("create_opportunity error: %s", exc)
            return None

    async def get_opportunities(
        self,
        opportunity_type: Optional[str] = None,
        country: Optional[str] = None,
        status: Optional[str] = None,
        upcoming_only: bool = False,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """Query opportunities."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import PlatformOpportunity

        try:
            async with get_session() as session:
                stmt = select(PlatformOpportunity).order_by(
                    desc(PlatformOpportunity.relevance_score)
                ).limit(limit)

                if opportunity_type:
                    stmt = stmt.where(PlatformOpportunity.opportunity_type == opportunity_type)
                if country:
                    stmt = stmt.where(PlatformOpportunity.country == country)
                if status:
                    stmt = stmt.where(PlatformOpportunity.status_code == status)
                if upcoming_only:
                    now = datetime.now(timezone.utc)
                    stmt = stmt.where(
                        or_(
                            PlatformOpportunity.event_start.is_(None),
                            PlatformOpportunity.event_start >= now,
                        )
                    )

                result = await session.execute(stmt)
                return [
                    {
                        "id": o.id, "type": o.opportunity_type, "name": o.name,
                        "description": o.description, "url": o.url,
                        "country": o.country, "city": o.city,
                        "event_start": str(o.event_start) if o.event_start else None,
                        "relevance_score": o.relevance_score, "status": o.status_code,
                    }
                    for o in result.scalars().all()
                ]
        except Exception:
            return []

    # ──────────────────────────────────────────────────────
    # Market Reports
    # ──────────────────────────────────────────────────────

    async def store_report(self, data: Dict[str, Any]) -> Optional[int]:
        """Store a market analysis report."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import MarketReport

        try:
            async with get_session() as session:
                report = MarketReport(
                    report_type=data["report_type"],
                    title=data["title"],
                    summary=data["summary"],
                    full_report=json.dumps(data.get("full_report", {}), ensure_ascii=False),
                    recommendations=json.dumps(data.get("recommendations", []), ensure_ascii=False),
                    scope_countries=json.dumps(data.get("scope_countries", []), ensure_ascii=False),
                    scope_platforms=json.dumps(data.get("scope_platforms", []), ensure_ascii=False),
                    metrics=json.dumps(data.get("metrics", {}), ensure_ascii=False),
                )
                session.add(report)
                await session.flush()
                return report.id
        except Exception as exc:
            logger.error("store_report error: %s", exc)
            return None

    async def get_latest_report(self, report_type: str) -> Optional[Dict[str, Any]]:
        """Get the most recent report of a given type."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import MarketReport

        try:
            async with get_session() as session:
                result = await session.execute(
                    select(MarketReport)
                    .where(MarketReport.report_type == report_type)
                    .order_by(desc(MarketReport.created_at))
                    .limit(1)
                )
                r = result.scalar_one_or_none()
                if not r:
                    return None
                return {
                    "id": r.id, "type": r.report_type, "title": r.title,
                    "summary": r.summary, "created_at": str(r.created_at),
                    "full_report": json.loads(r.full_report) if r.full_report else {},
                    "recommendations": json.loads(r.recommendations) if r.recommendations else [],
                }
        except Exception:
            return None

    # ──────────────────────────────────────────────────────
    # Marketing Events (Learning Loop)
    # ──────────────────────────────────────────────────────

    async def log_event(
        self,
        event_type: str,
        *,
        prospect_id: Optional[int] = None,
        campaign_id: Optional[int] = None,
        email_id: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        outcome: Optional[str] = None,
        score_delta: float = 0.0,
    ) -> Optional[int]:
        """Log a marketing event for the learning loop."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import MarketingEvent

        try:
            async with get_session() as session:
                event = MarketingEvent(
                    event_type=event_type,
                    prospect_id=prospect_id,
                    campaign_id=campaign_id,
                    email_id=email_id,
                    data=json.dumps(data, ensure_ascii=False) if data else None,
                    outcome=outcome,
                    score_delta=score_delta,
                )
                session.add(event)
                await session.flush()
                self._stats["events_logged"] += 1
                return event.id
        except Exception as exc:
            logger.error("log_event error: %s", exc)
            return None

    async def get_events(
        self,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query marketing events."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import MarketingEvent

        try:
            async with get_session() as session:
                stmt = select(MarketingEvent).order_by(desc(MarketingEvent.created_at)).limit(limit)
                if event_type:
                    stmt = stmt.where(MarketingEvent.event_type == event_type)
                if since:
                    stmt = stmt.where(MarketingEvent.created_at >= since)
                result = await session.execute(stmt)
                return [
                    {
                        "id": e.id, "type": e.event_type,
                        "prospect_id": e.prospect_id, "campaign_id": e.campaign_id,
                        "outcome": e.outcome, "score_delta": e.score_delta,
                        "created_at": str(e.created_at),
                        "data": json.loads(e.data) if e.data else None,
                    }
                    for e in result.scalars().all()
                ]
        except Exception:
            return []

    async def get_learning_insights(self, days: int = 30) -> Dict[str, Any]:
        """
        Aggregate event data to extract learning insights.
        Used by MarketingMasterAgent to tune strategies.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        events = await self.get_events(since=since, limit=1000)

        insights = {
            "total_events": len(events),
            "by_type": {},
            "success_rate_by_type": {},
            "best_countries": {},
            "best_categories": {},
        }

        type_counts: Dict[str, Dict[str, int]] = {}
        for evt in events:
            t = evt["type"]
            if t not in type_counts:
                type_counts[t] = {"total": 0, "success": 0, "failure": 0}
            type_counts[t]["total"] += 1
            if evt.get("outcome") == "success":
                type_counts[t]["success"] += 1
            elif evt.get("outcome") == "failure":
                type_counts[t]["failure"] += 1

        for t, counts in type_counts.items():
            insights["by_type"][t] = counts["total"]
            total = counts["total"]
            if total > 0:
                insights["success_rate_by_type"][t] = round(
                    counts["success"] / total * 100, 1
                )

        return insights

    # ──────────────────────────────────────────────────────
    # GDPR Consent
    # ──────────────────────────────────────────────────────

    async def record_consent(
        self,
        prospect_id: int,
        lawful_basis: str,
        purpose: str,
        *,
        consented: bool = True,
        consent_method: Optional[str] = None,
        consent_proof: Optional[str] = None,
    ) -> Optional[int]:
        """Record a GDPR consent/basis for a prospect."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import GDPRConsent

        try:
            async with get_session() as session:
                record = GDPRConsent(
                    prospect_id=prospect_id,
                    lawful_basis=lawful_basis,
                    purpose=purpose,
                    consented=consented,
                    consent_method=consent_method,
                    consent_proof=consent_proof,
                    granted_at=datetime.now(timezone.utc) if consented else None,
                )
                session.add(record)
                await session.flush()
                return record.id
        except Exception as exc:
            logger.error("record_consent error: %s", exc)
            return None

    async def check_consent(self, prospect_id: int, purpose: str) -> bool:
        """Check if a prospect has active consent for a purpose."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import GDPRConsent

        try:
            async with get_session() as session:
                result = await session.execute(
                    select(GDPRConsent)
                    .where(
                        and_(
                            GDPRConsent.prospect_id == prospect_id,
                            GDPRConsent.purpose == purpose,
                            GDPRConsent.revoked_at.is_(None),
                        )
                    )
                    .order_by(desc(GDPRConsent.created_at))
                    .limit(1)
                )
                consent = result.scalar_one_or_none()
                if consent is None:
                    return False
                # Check if it uses legitimate interest (always valid for B2B)
                if consent.lawful_basis == "legitimate_interest":
                    return True
                return consent.consented
        except Exception:
            return False

    async def revoke_consent(self, prospect_id: int, purpose: str) -> bool:
        """Revoke consent and opt out the prospect."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import GDPRConsent, Prospect

        now = datetime.now(timezone.utc)
        try:
            async with get_session() as session:
                await session.execute(
                    update(GDPRConsent)
                    .where(
                        and_(
                            GDPRConsent.prospect_id == prospect_id,
                            GDPRConsent.purpose == purpose,
                            GDPRConsent.revoked_at.is_(None),
                        )
                    )
                    .values(revoked_at=now)
                )
                await session.execute(
                    update(Prospect)
                    .where(Prospect.id == prospect_id)
                    .values(opted_out=True)
                )
                return True
        except Exception as exc:
            logger.error("revoke_consent error: %s", exc)
            return False

    async def gdpr_erase_prospect(self, prospect_id: int) -> Dict[str, int]:
        """GDPR Article 17 — right to erasure for a prospect and all related data."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import (
            Prospect, OutreachEmail, GDPRConsent, MarketingEvent,
        )

        counts: Dict[str, int] = {}
        try:
            async with get_session() as session:
                for name, model, col in [
                    ("emails", OutreachEmail, OutreachEmail.prospect_id),
                    ("consents", GDPRConsent, GDPRConsent.prospect_id),
                    ("events", MarketingEvent, MarketingEvent.prospect_id),
                ]:
                    result = await session.execute(
                        delete(model).where(col == prospect_id)
                    )
                    counts[name] = result.rowcount

                result = await session.execute(
                    delete(Prospect).where(Prospect.id == prospect_id)
                )
                counts["prospect"] = result.rowcount
                return counts
        except Exception as exc:
            logger.error("gdpr_erase error: %s", exc)
            return counts

    async def cleanup_expired_data(self, retention_days: int = 730) -> Dict[str, int]:
        """Delete data older than retention period (GDPR compliance)."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import MarketingEvent, MarketReport

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        counts: Dict[str, int] = {}
        try:
            async with get_session() as session:
                result = await session.execute(
                    delete(MarketingEvent).where(MarketingEvent.created_at < cutoff)
                )
                counts["events"] = result.rowcount

                result = await session.execute(
                    delete(MarketReport).where(MarketReport.created_at < cutoff)
                )
                counts["reports"] = result.rowcount
                return counts
        except Exception as exc:
            logger.error("cleanup error: %s", exc)
            return counts

    # ──────────────────────────────────────────────────────
    # Dashboard Aggregations
    # ──────────────────────────────────────────────────────

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get overview stats for the marketing dashboard."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import (
            Prospect, OutreachCampaign, OutreachEmail,
            PlatformListing, PlatformOpportunity,
        )

        stats: Dict[str, Any] = {}
        try:
            async with get_session() as session:
                # Prospect counts by status
                result = await session.execute(
                    select(Prospect.status_code, func.count())
                    .group_by(Prospect.status_code)
                )
                stats["prospects"] = {row[0]: row[1] for row in result.all()}

                # Campaign counts
                result = await session.execute(
                    select(func.count()).select_from(OutreachCampaign)
                    .where(OutreachCampaign.status_code == "active")
                )
                stats["active_campaigns"] = result.scalar() or 0

                # Email stats
                result = await session.execute(
                    select(OutreachEmail.status_code, func.count())
                    .group_by(OutreachEmail.status_code)
                )
                stats["emails"] = {row[0]: row[1] for row in result.all()}

                # Listing counts
                result = await session.execute(
                    select(PlatformListing.status_code, func.count())
                    .group_by(PlatformListing.status_code)
                )
                stats["listings"] = {row[0]: row[1] for row in result.all()}

                # Opportunities
                result = await session.execute(
                    select(func.count()).select_from(PlatformOpportunity)
                    .where(PlatformOpportunity.status_code == "discovered")
                )
                stats["new_opportunities"] = result.scalar() or 0

        except Exception as exc:
            stats["error"] = str(exc)

        return stats

    # ──────────────────────────────────────────────────────
    # Serialisation Helpers
    # ──────────────────────────────────────────────────────

    @staticmethod
    def _prospect_to_dict(p: Any) -> Dict[str, Any]:
        return {
            "id": p.id,
            "business_name": p.business_name,
            "business_type": p.business_type,
            "website": p.website,
            "email": p.email,
            "phone": p.phone,
            "contact_person": p.contact_person,
            "contact_role": p.contact_role,
            "country": p.country,
            "city": p.city,
            "region": p.region,
            "score": p.score,
            "status": p.status_code,
            "source": p.source,
            "language": p.language,
            "opted_out": p.opted_out,
            "discovered_at": str(p.discovered_at) if p.discovered_at else None,
            "last_contacted_at": str(p.last_contacted_at) if p.last_contacted_at else None,
            "tags": json.loads(p.tags) if p.tags else [],
        }

    @staticmethod
    def _campaign_to_dict(c: Any) -> Dict[str, Any]:
        return {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "status": c.status_code,
            "total_prospects": c.total_prospects,
            "emails_sent": c.emails_sent,
            "emails_opened": c.emails_opened,
            "emails_replied": c.emails_replied,
            "emails_bounced": c.emails_bounced,
            "ab_test_enabled": c.ab_test_enabled,
            "created_at": str(c.created_at) if c.created_at else None,
            "target_countries": json.loads(c.target_countries) if c.target_countries else [],
            "target_categories": json.loads(c.target_categories) if c.target_categories else [],
        }

    @staticmethod
    def _email_to_dict(e: Any) -> Dict[str, Any]:
        return {
            "id": e.id,
            "campaign_id": e.campaign_id,
            "prospect_id": e.prospect_id,
            "sequence_step": e.sequence_step,
            "to_email": e.to_email,
            "subject": e.subject,
            "body_html": e.body_html,
            "language": e.language,
            "status": e.status_code,
            "sent_at": str(e.sent_at) if e.sent_at else None,
        }

    # ── OMEGA: Recon Storage ──────────────────────────────

    async def store_recon_report(self, prospect_id: int, report_dict: Dict[str, Any]) -> bool:
        """Store deep recon data in the prospect's extra_data field."""
        prospect = await self.get_prospect(prospect_id)
        if not prospect: return False
        
        extra_data = prospect.get("extra_data", {})
        if isinstance(extra_data, str):
            try:
                extra_data = json.loads(extra_data)
            except:
                extra_data = {}
            
        extra_data["recon_report"] = report_dict
        return await self.update_prospect(prospect_id, {"extra_data": json.dumps(extra_data, ensure_ascii=False)})

    async def get_recon_report(self, prospect_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve deep recon data for a prospect."""
        prospect = await self.get_prospect(prospect_id)
        if not prospect: return None
        
        extra_data = prospect.get("extra_data", {})
        if isinstance(extra_data, str):
            try:
                extra_data = json.loads(extra_data)
            except:
                extra_data = {}
            
        return extra_data.get("recon_report")

    async def get_dashboard_stats_v2(self) -> Dict[str, Any]:
        """Get high-level marketing statistics for the dashboard."""
        from arki_project.database.connection import get_session
        from arki_project.database.marketing_models import OutreachCampaign, OutreachEmail, MarketingEvent

        stats = {
            "total_prospects": 0,
            "qualified_prospects": 0,
            "active_campaigns": 0,
            "total_emails_sent": 0,
            "recent_events": 0,
        }

        try:
            async with get_session() as session:
                # Prospects
                stats["total_prospects"] = await self.count_prospects()
                stats["qualified_prospects"] = await self.count_prospects(status="qualified")
                
                # Campaigns
                campaign_count = await session.execute(
                    select(func.count()).select_from(OutreachCampaign).where(OutreachCampaign.status_code == "active")
                )
                stats["active_campaigns"] = campaign_count.scalar() or 0
                
                # Emails
                email_count = await session.execute(
                    select(func.count()).select_from(OutreachEmail).where(OutreachEmail.status_code == "sent")
                )
                stats["total_emails_sent"] = email_count.scalar() or 0
                
                # Recent events (last 24h)
                yesterday = datetime.now(timezone.utc) - timedelta(days=1)
                event_count = await session.execute(
                    select(func.count()).select_from(MarketingEvent).where(MarketingEvent.created_at >= yesterday)
                )
                stats["recent_events"] = event_count.scalar() or 0
                
                return stats
        except Exception as exc:
            logger.error("get_dashboard_stats error: %s", exc)
            return stats


# ── Singleton ──
_bridge: Optional[MarketingDataBridge] = None


def get_data_bridge() -> MarketingDataBridge:
    """Get or create the singleton data bridge."""
    global _bridge
    if _bridge is None:
        _bridge = MarketingDataBridge()
    return _bridge



_bridge_instance = None

def get_data_bridge() -> MarketingDataBridge:
    """Singleton helper to get the data bridge."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = MarketingDataBridge()
    return _bridge_instance


