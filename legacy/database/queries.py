
from __future__ import annotations
"""
tg_bot/database/queries.py — Optimized queries v29.0
Common database queries with N+1 prevention and proper indexes.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from arki_project.database.models import (
    User, ChatMessage, AnalyticsEvent, Subscription,
)

logger = logging.getLogger(__name__)


async def get_user_with_messages(
    session: AsyncSession,
    user_id: int,
    limit: int = 50,
) -> Tuple[Optional[Any], List[Any]]:
    """
    Get user + last N messages in TWO efficient queries (not N+1).

    v29.0: Replaced broken selectinload(User.messages) — User model
    has no 'messages' relationship. Now uses two indexed queries.
    """
    # Query 1: User by PK (instant)
    user_result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        return None, []

    # Query 2: Messages by indexed user_id + created_at (ix_chat_messages_user_created)
    msg_result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    messages = msg_result.scalars().all()

    return user, messages


async def get_active_users_batch(
    session: AsyncSession,
    since_hours: int = 24,
) -> List[Any]:
    """Get all users active in last N hours with message counts (single query)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    result = await session.execute(
        select(
            User.telegram_id,
            User.username,
            Subscription.plan,
            func.count(ChatMessage.id).label("msg_count"),
        )
        .outerjoin(Subscription, User.telegram_id == Subscription.user_id)
        .outerjoin(ChatMessage, User.telegram_id == ChatMessage.user_id)
        .where(ChatMessage.created_at >= cutoff)
        .group_by(User.telegram_id, Subscription.plan)
        .order_by(func.count(ChatMessage.id).desc())
    )
    return result.fetchall()


async def get_analytics_summary(
    session: AsyncSession,
    days: int = 30,
) -> Dict[str, Any]:
    """Get aggregated analytics — three efficient indexed queries."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    total_users = (await session.execute(
        select(func.count()).select_from(User)
    )).scalar() or 0

    total_messages = (await session.execute(
        select(func.count()).select_from(ChatMessage)
        .where(ChatMessage.created_at >= cutoff)
    )).scalar() or 0

    # Top models — uses ix_analytics_event_type composite index
    top_models = await session.execute(
        select(AnalyticsEvent.model_used, func.count().label("cnt"))
        .where(AnalyticsEvent.created_at >= cutoff)
        .where(AnalyticsEvent.model_used != "")
        .group_by(AnalyticsEvent.model_used)
        .order_by(func.count().desc())
        .limit(10)
    )

    return {
        "total_users": total_users,
        "total_messages": total_messages,
        "top_models": [(r[0], r[1]) for r in top_models.fetchall()],
    }


async def bulk_update_token_usage(
    session: AsyncSession,
    user_ids: List[int],
    reset: bool = False,
) -> int:
    """Batch update token usage for multiple users (prevents N+1 updates).

    Returns number of affected rows.
    """
    if not user_ids:
        return 0
    if reset:
        result = await session.execute(
            update(User)
            .where(User.telegram_id.in_(user_ids))
            .values(tokens_used_today=0)
        )
        await session.commit()
        return result.rowcount  # type: ignore[return-value]
    return 0


async def get_user_message_stats(
    session: AsyncSession,
    user_id: int,
    days: int = 30,
) -> Dict[str, Any]:
    """Get per-user message + token stats in one query.

    v29.0: New optimized query using composite index.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await session.execute(
        select(
            func.count(ChatMessage.id).label("msg_count"),
            func.sum(ChatMessage.tokens_used).label("total_tokens"),
            func.min(ChatMessage.created_at).label("first_msg"),
            func.max(ChatMessage.created_at).label("last_msg"),
        )
        .where(ChatMessage.user_id == user_id)
        .where(ChatMessage.created_at >= cutoff)
    )
    row = result.one()
    return {
        "message_count": row.msg_count or 0,
        "total_tokens": row.total_tokens or 0,
        "first_message": row.first_msg,
        "last_message": row.last_msg,
    }


async def health_check(session: AsyncSession) -> bool:
    """Check database connectivity."""
    try:
        await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


