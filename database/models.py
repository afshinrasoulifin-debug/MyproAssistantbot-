
from __future__ import annotations
"""
tg_bot/database/models.py
─────────────────────────
SQLAlchemy 2.0 declarative models.

v29.0.0:
  • AnalyticsEvent table — command usage, response times, errors
  • ScheduledTask table — recurring tasks, cron-like scheduling
  • UserSession table — track active sessions, last activity
  • Better indexes for common queries
  • Cascade-ready relationships
  • Audit timestamps on all tables

Tables:
  users           — registered Telegram users
  user_configs    — per-user settings (model, persona, autotune, voice)
  chat_messages   — conversation persistence
  kv_store        — generic key-value persistence (products, brands, etc.)
  reminders       — user-scheduled reminders
  user_notes      — simple note/memo storage
  customers       — CRM records
  finance_records — income/expense tracking
  web_monitors    — web page change monitor
  auto_replies    — keyword-triggered auto-responses
  analytics_events— command usage & performance tracking (NEW)
  scheduled_tasks — cron-like task scheduling (NEW)
"""


import datetime
from typing import Optional
import uuid # Added for Campaign ID generation

import sqlalchemy as sa  # v10.2: FIX — required for sa.DateTime, sa.ForeignKey etc.
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass

class SoftDeleteMixin:
    """v9.4: Mixin for soft delete — marks records as deleted instead of removing."""
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True, default=None)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)

    def soft_delete(self):
        from datetime import datetime, timezone
        self.deleted_at = datetime.now(timezone.utc)
        self.is_deleted = True

    def restore(self):
        self.deleted_at = None
        self.is_deleted = False



class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False,
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, default=None,
    )
    full_name: Mapped[str] = mapped_column(
        String(256), nullable=False, default="",
    )
    language: Mapped[str] = mapped_column(
        String(8), nullable=False, default="fa",
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    last_active: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    is_banned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True,  # v29.0: indexed — admin queries filter by banned
    )
    is_premium: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    total_tokens_used: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0,
    )
    referral_code: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, unique=True,
    )
    referred_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True,
    )
    tokens_used_today: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0,
    )
    daily_token_budget: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=50000,
    )
    # v29.0: User tier for rate limiting (free/pro/enterprise/unlimited)
    tier: Mapped[str] = mapped_column(
        String(16), nullable=False, default="free", index=True,
    )


class UserConfig(Base):
    """Per-user preferences: chosen model, persona, autotune, voice."""

    __tablename__ = "user_configs"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False,
    )
    model: Mapped[str] = mapped_column(
        String(64), nullable=False, default="gemini-pro"  # v9.7.1,
    )
    persona: Mapped[str] = mapped_column(
        String(32), nullable=False, default="assistant",
    )
    autotune: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    voice: Mapped[str] = mapped_column(
        String(32), nullable=False, default="Zephyr",
    )
    language: Mapped[str] = mapped_column(
        String(8), nullable=False, default="fa",
    )
    max_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=8192,
    )
    temperature: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.7,
    )


class KVStore(Base):
    """
    Generic key-value store for persistent data.

    Used for: products, brands, shop_profiles, catalogs, queues, sales.
    Each row = one store + one chat_id → JSON blob.
    """

    __tablename__ = "kv_store"

    store_name: Mapped[str] = mapped_column(
        String(64), primary_key=True,
    )
    chat_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True,
    )
    data: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}",
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )


class Reminder(Base):
    """User-scheduled reminders with recurring support."""

    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True,
    )
    chat_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    remind_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    sent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True,  # v29.0: indexed — reminder scheduler queries unsent
    )
    # v7: recurring reminders
    is_recurring: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    recurrence_rule: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True,  # "daily", "weekly", "monthly", or cron-like
    )


class UserNote(Base):
    """Simple note/memo storage per user with tags."""

    __tablename__ = "user_notes"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(
        String(256), nullable=False, default="",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[str] = mapped_column(
        String(256), nullable=False, default="",
    )
    is_pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )


class Customer(Base):
    """CRM — customer records with enhanced tracking."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    owner_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(
        String(256), nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(256), nullable=False, default="",
    )
    phone: Mapped[str] = mapped_column(
        String(32), nullable=False, default="",
    )
    note: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
    )
    tags: Mapped[str] = mapped_column(
        String(256), nullable=False, default="",
    )
    source: Mapped[str] = mapped_column(
        String(64), nullable=False, default="",  # "instagram", "etsy", "tori", "direct"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True,  # v29.0: indexed — CRM status filter
    )
    total_orders: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    total_spent: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0,
    )
    last_order_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    segment: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown", index=True)
    tags: Mapped[str] = mapped_column(String(256), nullable=False, default="[]") # JSON string
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    command_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ai_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    referrals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    engagement_history: Mapped[str] = mapped_column(Text, nullable=False, default="[]") # JSON string
    
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )


class Campaign(Base, SoftDeleteMixin):
    __tablename__ = "campaigns"

    campaign_id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:10]
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(32), nullable=False, default="broadcast")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    target_segment: Mapped[str] = mapped_column(String(64), nullable=False, default="all")
    messages: Mapped[str] = mapped_column(Text, nullable=False, default="[]") # JSON string
    variants: Mapped[str] = mapped_column(Text, nullable=False, default="{}") # JSON string
    schedule: Mapped[str] = mapped_column(Text, nullable=False, default="{}") # JSON string
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opened: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    converted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unsubscribed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class FinanceRecord(Base):
    """Income/expense tracking with categories."""

    __tablename__ = "finance_records"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True,
    )
    amount: Mapped[int] = mapped_column(
        BigInteger, nullable=False,  # positive=income, negative=expense
    )
    currency: Mapped[str] = mapped_column(
        String(8), nullable=False, default="EUR",
    )
    category: Mapped[str] = mapped_column(
        String(128), nullable=False, default="",
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
    )
    platform: Mapped[str] = mapped_column(
        String(64), nullable=False, default="",  # "etsy", "tori", "cash"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )


class WebMonitor(Base):
    """Web page change monitor with enhanced tracking."""

    __tablename__ = "web_monitors"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True,
    )
    chat_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False,
    )
    url: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    label: Mapped[str] = mapped_column(
        String(256), nullable=False, default="",
    )
    css_selector: Mapped[str] = mapped_column(
        String(256), nullable=False, default="",  # v7: target specific element
    )
    last_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, default="",
    )
    last_size: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    last_checked: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    last_changed: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    check_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    change_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True,  # v29.0: indexed — monitor scheduler
    )
    check_interval_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )


class AutoReply(Base):
    """Keyword-triggered auto-responses with enhanced matching."""

    __tablename__ = "auto_replies"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True,
    )
    trigger: Mapped[str] = mapped_column(
        String(256), nullable=False,
    )
    response: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    match_mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default="contains",  # "exact", "contains", "regex", "starts_with"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True,  # v29.0: indexed — auto-reply filter
    )
    use_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True,
    )
    role: Mapped[str] = mapped_column(
        String(10), nullable=False,
    )  # "user" | "model"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True,
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )


# ═══════════════════ NEW v7 TABLES ═══════════════════

class AnalyticsEvent(Base):
    """Track command usage, response times, and errors for analytics."""

    __tablename__ = "analytics_events"
    __table_args__ = (
        Index("ix_analytics_user_created", "user_id", "created_at"),
        Index("ix_analytics_event_type", "event_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False,
    )
    event_type: Mapped[str] = mapped_column(
        String(32), nullable=False,  # "command", "callback", "message", "error"
    )
    command: Mapped[str] = mapped_column(
        String(64), nullable=False, default="",
    )
    model_used: Mapped[str] = mapped_column(
        String(64), nullable=False, default="",
    )
    response_time_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    tokens_in: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    tokens_out: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    success: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True,  # v29.0: indexed — admin error dashboard
    )
    error_message: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
    )
    metadata_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}",
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )


class ScheduledTask(Base):
    """Cron-like task scheduling for automation."""

    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True,
    )
    chat_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False,
    )
    task_type: Mapped[str] = mapped_column(
        String(64), nullable=False,  # "content_batch", "report", "backup", "digest"
    )
    schedule: Mapped[str] = mapped_column(
        String(64), nullable=False,  # "daily", "weekly", "monthly" or cron expression
    )
    config_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    last_run: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    next_run: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True,
    )
    run_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    last_error: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    # v10.3.1: Composite indices for faster task scheduling queries
    __table_args__ = (
        Index("ix_scheduled_tasks_user_active", "user_id", "is_active"),
        Index("ix_scheduled_tasks_type_active", "task_type", "is_active"),
    )


# ═══ v7 Extra Models (merged from models_v7_extra.py) ═══

class SemanticMemory(Base):
    """Long-term semantic memory for conversations."""
    __tablename__ = "semantic_memory"
    __table_args__ = (
        Index("ix_semantic_memory_user_ns", "user_id", "namespace"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    namespace: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False, default="conversation")
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )


    last_accessed: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )



class KnowledgeEntity(Base):
    """Knowledge graph entities extracted from conversations."""
    __tablename__ = "knowledge_entities"
    __table_args__ = (
        Index("ix_knowledge_entity_user", "user_id", "entity_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    entity_name: Mapped[str] = mapped_column(String(256), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    properties_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    relations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )



class PipelineLog(Base):
    """Log every pipeline execution for debugging and analytics."""
    __tablename__ = "pipeline_logs"
    __table_args__ = (
        Index("ix_pipeline_log_user_ts", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    request_id: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    complexity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reasoning_strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    modules_used: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )



class WorkflowExecution(Base):
    """Track workflow engine executions."""
    __tablename__ = "workflow_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    workflow_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    steps_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    steps_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )



class TelemetryMetric(Base):
    """Aggregated telemetry metrics."""
    __tablename__ = "telemetry_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    tags_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )




# ═══ v9.4: Billing & Subscription Models ═══

class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("users.telegram_id"), unique=True, index=True)
    plan: Mapped[str] = mapped_column(sa.String(20), default="free")
    started_at: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True), default=sa.func.now())
    expires_at: Mapped[Optional[datetime.datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    is_trial: Mapped[bool] = mapped_column(default=False)
    auto_renew: Mapped[bool] = mapped_column(default=False)
    payment_method: Mapped[str] = mapped_column(sa.String(50), default="")
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)


class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("users.telegram_id"), index=True)
    plan: Mapped[str] = mapped_column(sa.String(20))
    amount: Mapped[float] = mapped_column(sa.Float, default=0.0)
    currency: Mapped[str] = mapped_column(sa.String(10), default="USD")
    status: Mapped[str] = mapped_column(sa.String(20), default="pending")
    created_at: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True), default=sa.func.now())
    paid_at: Mapped[Optional[datetime.datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)


class ReferralCode(Base):
    __tablename__ = "referral_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(sa.String(20), unique=True, index=True)
    referrer_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("users.telegram_id"), index=True)
    referred_id: Mapped[Optional[int]] = mapped_column(sa.BigInteger, nullable=True)
    reward_given: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True), default=sa.func.now())


class AuditEntry(Base):
    __tablename__ = "audit_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, index=True)
    action: Mapped[str] = mapped_column(sa.String(50), index=True)
    resource: Mapped[str] = mapped_column(sa.String(200), default="")
    details: Mapped[str] = mapped_column(sa.Text, default="")
    ip_address: Mapped[str] = mapped_column(sa.String(50), default="")
    created_at: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True), default=sa.func.now())


class TokenUsage(Base):
    __tablename__ = "token_usage"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("users.telegram_id"), index=True)
    model: Mapped[str] = mapped_column(sa.String(50))
    handler: Mapped[str] = mapped_column(sa.String(50))
    input_tokens: Mapped[int] = mapped_column(sa.Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(sa.Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(sa.Float, default=0.0)
    created_at: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True), default=sa.func.now())


    __table_args__ = (
        Index("ix_token_usage_user_created", "user_id", "created_at"),
    )


# ── Marketing TITAN Tables ──────────────────────────────
# Import marketing models so Base.metadata.create_all() picks them up.
try:
    from arki_project.database.marketing_models import (  # noqa: F401
        Prospect, OutreachCampaign, OutreachSequence, OutreachEmail,
        PlatformListing, PlatformOpportunity, MarketReport,
        MarketingEvent, GDPRConsent,
    )
except ImportError:
    pass  # Marketing TITAN module not installed


class ModelPerformanceState(Base):
    """Persistent model performance state — survives restarts.
    
    v26.1: Stores demote/promote status and key metrics so analytics
    don't reset on bot restart.
    """
    __tablename__ = "model_performance_state"
    __table_args__ = (
        Index("ix_mps_model_key", "model_key", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    total_calls: Mapped[int] = mapped_column(default=0)
    successes: Mapped[int] = mapped_column(default=0)
    failures: Mapped[int] = mapped_column(default=0)
    total_latency_ms: Mapped[float] = mapped_column(default=0.0)
    avg_quality: Mapped[float] = mapped_column(default=0.0)
    demoted: Mapped[bool] = mapped_column(default=False)
    demoted_at: Mapped[Optional[datetime.datetime]] = mapped_column(nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


