
from __future__ import annotations
"""
tg_bot/database/marketing_models.py — Marketing Agent TITAN Database Models
═══════════════════════════════════════════════════════════════════════════════
9 new SQLAlchemy 2.0 tables for the autonomous marketing intelligence system.

Tables
──────
  prospects              — B2B prospect businesses with geo/category/score
  outreach_campaigns     — Multi-sequence email campaigns
  outreach_sequences     — Email sequence step definitions
  outreach_emails        — Individual emails with open/click tracking
  platform_listings      — Cross-platform product listings
  platform_opportunities — Discovered new platforms & physical markets
  market_reports         — Strategic analysis snapshots
  marketing_events       — Event log for the learning loop
  gdpr_consents          — GDPR consent & data-processing records

All models use the shared ``Base`` from ``database.models`` so they
participate in the same ``create_all`` call during ``init_db()``.
"""


import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from arki_project.database.models import Base


# ═══════════════════════════════════════════════════════════
# 1. Prospects — B2B Target Businesses
# ═══════════════════════════════════════════════════════════

class Prospect(Base):
    """
    A discovered B2B prospect (hotel, restaurant, spa, gallery, etc.).

    Lifecycle:  discovered → qualified → contacted → responded → converted / rejected
    """

    __tablename__ = "prospects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Identity ──
    business_name: Mapped[str] = mapped_column(String(512), nullable=False)
    business_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # hotel, restaurant, spa …
    website: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    contact_person: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    contact_role: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # ── Geography ──
    country: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Scoring ──
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    score_factors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON dict of factor→value

    # ── Status ──
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="discovered", index=True,
    )  # discovered, qualified, contacted, responded, converted, rejected, blacklisted

    # ── Source ──
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="b2b_hunter")
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    source_query: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # ── Metadata ──
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    timezone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    extra_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON blob

    # ── GDPR ──
    gdpr_basis: Mapped[str] = mapped_column(
        String(32), nullable=False, default="legitimate_interest",
    )  # legitimate_interest, consent
    gdpr_consent_date: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    opted_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── Timestamps ──
    discovered_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    last_contacted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    last_responded_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )

    # ── Deduplication ──
    fingerprint: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, unique=True,
    )  # SimHash or normalized name+city hash

    __table_args__ = (
        Index("ix_prospects_country_type", "country", "business_type"),
        Index("ix_prospects_status_score", "status", "score"),
    )


# ═══════════════════════════════════════════════════════════
# 2. Outreach Campaigns
# ═══════════════════════════════════════════════════════════

class OutreachCampaign(Base):
    """
    A multi-step email outreach campaign targeting a set of prospects.

    Lifecycle:  draft → active → paused → completed / cancelled
    """

    __tablename__ = "outreach_campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Targeting ──
    target_countries: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    target_categories: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    min_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # ── Status ──
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", index=True,
    )  # draft, active, paused, completed, cancelled
    total_prospects: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    emails_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    emails_opened: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    emails_replied: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    emails_bounced: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── A/B Testing ──
    ab_test_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ab_test_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # ── Timestamps ──
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )

    # ── Owner ──
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


# ═══════════════════════════════════════════════════════════
# 3. Outreach Sequences — Email Step Definitions
# ═══════════════════════════════════════════════════════════

class OutreachSequence(Base):
    """
    A single step in an outreach campaign's email sequence.

    Example 4-step sequence:
      Step 0: Introduction + product highlights (day 0)
      Step 1: Follow-up with social proof (day 3)
      Step 2: Catalog / portfolio attachment (day 7)
      Step 3: Special offer / last chance (day 14)
    """

    __tablename__ = "outreach_sequences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer, sa.ForeignKey("outreach_campaigns.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    delay_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Content ──
    subject_template: Mapped[str] = mapped_column(Text, nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    attach_catalog: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── A/B Variants ──
    variant_label: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # "A", "B", None

    __table_args__ = (
        Index("ix_seq_campaign_step", "campaign_id", "step_number"),
    )


# ═══════════════════════════════════════════════════════════
# 4. Outreach Emails — Individual Sent Emails
# ═══════════════════════════════════════════════════════════

class OutreachEmail(Base):
    """
    An individual email sent to a prospect as part of a campaign sequence.
    Tracks delivery, opens, clicks, and replies.
    """

    __tablename__ = "outreach_emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer, sa.ForeignKey("outreach_campaigns.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    prospect_id: Mapped[int] = mapped_column(
        Integer, sa.ForeignKey("prospects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    sequence_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Content snapshot ──
    to_email: Mapped[str] = mapped_column(String(512), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    variant_label: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # ── Delivery ──
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="queued", index=True,
    )  # queued, sent, delivered, opened, clicked, replied, bounced, failed
    sent_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    replied_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    bounced_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Provider ──
    provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # smtp, sendgrid, resend
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Timestamps ──
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_email_campaign_prospect", "campaign_id", "prospect_id"),
        Index("ix_email_status_sent", "status", "sent_at"),
    )


# ═══════════════════════════════════════════════════════════
# 5. Platform Listings
# ═══════════════════════════════════════════════════════════

class PlatformListing(Base):
    """
    A product listing published (or to be published) on a marketplace.
    """

    __tablename__ = "platform_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(512), nullable=False)

    # ── Content ──
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    price_eur: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="EUR")
    images: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of URLs
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")

    # ── Status ──
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", index=True,
    )  # draft, published, paused, sold_out, expired, removed
    external_listing_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    external_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # ── Performance ──
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    favorites: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sales: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue_eur: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # ── Timestamps ──
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    published_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_listing_platform_status", "platform_key", "status"),
    )


# ═══════════════════════════════════════════════════════════
# 6. Platform Opportunities — New Platforms & Physical Markets
# ═══════════════════════════════════════════════════════════

class PlatformOpportunity(Base):
    """
    A discovered platform, exhibition, Christmas market, or craft fair
    that the business could join or attend.
    """

    __tablename__ = "platform_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    opportunity_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True,
    )  # online_platform, exhibition, christmas_market, craft_fair, popup

    # ── Details ──
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # ── Dates (for physical events) ──
    event_start: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    event_end: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    application_deadline: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Assessment ──
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    estimated_cost_eur: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Status ──
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="discovered",
    )  # discovered, evaluating, applied, accepted, rejected, attended, skipped

    # ── Source ──
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="platform_scout")

    # ── Timestamps ──
    discovered_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )

    # ── Dedup ──
    fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)


# ═══════════════════════════════════════════════════════════
# 7. Market Reports — Strategic Analysis Snapshots
# ═══════════════════════════════════════════════════════════

class MarketReport(Base):
    """
    A snapshot of market analysis generated by the MarketProfessorEngine.
    """

    __tablename__ = "market_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
    )  # daily_brief, competitor_analysis, platform_ranking, trend_report, social_strategy

    # ── Content ──
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    full_report: Mapped[str] = mapped_column(Text, nullable=False)  # JSON structured data
    recommendations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list

    # ── Scope ──
    scope_countries: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    scope_platforms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list

    # ── Metrics snapshot ──
    metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: {total_prospects, emails_sent, …}

    # ── Timestamps ──
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )


# ═══════════════════════════════════════════════════════════
# 8. Marketing Events — Learning Loop Event Log
# ═══════════════════════════════════════════════════════════

class MarketingEvent(Base):
    """
    Event log for the marketing agent's learning loop.

    Every significant action (email sent, prospect found, reply received,
    campaign started) is logged here.  The MarketingMasterAgent uses this
    to detect patterns and improve future decisions.
    """

    __tablename__ = "marketing_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
    )  # prospect_found, email_sent, email_opened, email_replied, campaign_started, …

    # ── References ──
    prospect_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    email_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── Data ──
    data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON payload
    outcome: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # success, failure, neutral
    score_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # ── Timestamp ──
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True,
    )


# ═══════════════════════════════════════════════════════════
# 9. GDPR Consents — Consent & Data-Processing Records
# ═══════════════════════════════════════════════════════════

class GDPRConsent(Base):
    """
    GDPR consent and lawful-basis records for marketing data processing.
    Required for EU compliance — Article 6 & 7.
    """

    __tablename__ = "gdpr_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prospect_id: Mapped[int] = mapped_column(
        Integer, sa.ForeignKey("prospects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # ── Lawful Basis ──
    lawful_basis: Mapped[str] = mapped_column(
        String(64), nullable=False,
    )  # legitimate_interest, consent, contract, legal_obligation

    # ── Consent details ──
    purpose: Mapped[str] = mapped_column(
        String(256), nullable=False,
    )  # b2b_outreach, newsletter, product_updates
    consented: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_method: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True,
    )  # email_reply, web_form, verbal, implied_b2b
    consent_proof: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # reference/evidence

    # ── Timestamps ──
    granted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    revoked_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    expires_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_gdpr_prospect_purpose", "prospect_id", "purpose"),
    )


