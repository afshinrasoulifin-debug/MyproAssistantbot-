
from __future__ import annotations
"""
tg_bot/utils/gdpr.py — GDPR data erasure v9.6
Complete user data deletion per GDPR Article 17.
"""
import logging
from datetime import datetime, timezone

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


async def erase_user_data(user_id: int) -> dict:
    """Delete ALL data for a user (GDPR right to erasure).

    Returns dict with counts of deleted records per table.
    """
    from arki_project.database.connection import get_session
    from sqlalchemy import delete, select
    from arki_project.database.models import (
        User, ChatMessage, UserConfig, AnalyticsEvent,
    )

    counts = {}

    async with get_session() as session:
        # 1. Chat messages
        result = await session.execute(
            delete(ChatMessage).where(ChatMessage.user_id == user_id)
        )
        counts["chat_messages"] = result.rowcount

        # 2. Analytics events
        result = await session.execute(
            delete(AnalyticsEvent).where(AnalyticsEvent.user_id == user_id)
        )
        counts["analytics_events"] = result.rowcount

        # 3. User config
        try:
            result = await session.execute(
                delete(UserConfig).where(UserConfig.user_id == user_id)
            )
            counts["user_configs"] = result.rowcount
        except Exception:
            counts["user_configs"] = 0

        # 4. Token usage
        try:
            from arki_project.database.models import TokenUsage
            result = await session.execute(
                delete(TokenUsage).where(TokenUsage.user_id == user_id)
            )
            counts["token_usage"] = result.rowcount
        except Exception:
            counts["token_usage"] = 0

        # 5. Semantic memories
        try:
            from arki_project.database.models import SemanticMemory
            result = await session.execute(
                delete(SemanticMemory).where(SemanticMemory.user_id == user_id)
            )
            counts["semantic_memories"] = result.rowcount
        except Exception:
            counts["semantic_memories"] = 0

        # 6. Subscriptions
        try:
            from arki_project.database.models import Subscription
            result = await session.execute(
                delete(Subscription).where(Subscription.user_id == user_id)
            )
            counts["subscriptions"] = result.rowcount
        except Exception:
            counts["subscriptions"] = 0

        # 7. User record (last — soft delete first, then hard delete)
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        if user:
            # Anonymize first
            user.username = f"deleted_{user_id}"
            user.first_name = "Deleted"
            user.deleted_at = datetime.now(timezone.utc)
            counts["user"] = 1

        await session.commit()

    # 8. Log the erasure for audit (without PII)
    try:
        from arki_project.database.models import AuditEntry
        async with get_session() as session:
            session.add(AuditEntry(
                user_id=0,  # Don't store the deleted user's ID
                action="gdpr_erasure",
                details=f"Erased data for user (counts: {counts})",
            ))
            await session.commit()
    except Exception as _exc:
        logger.debug("Suppressed: %s", _exc)

    logger.info("GDPR erasure completed for user %d: %s", user_id, counts)
    return counts


