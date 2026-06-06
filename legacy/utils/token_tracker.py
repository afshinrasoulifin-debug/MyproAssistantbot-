
from __future__ import annotations
"""
tg_bot/utils/token_tracker.py — Centralized token usage tracker v9.7
Call from ANY handler after AI usage.
"""
import logging
from typing import Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


async def track_tokens(user_id: int, input_text: str = "", output_text: str = "", extra_tokens: int = 0) -> Any:
    """Update user's tokens_used_today in the database.

    Args:
        user_id: Telegram user ID
        input_text: Input text sent to AI (for approximate token count)
        output_text: Output text received from AI
        extra_tokens: Additional tokens to add (e.g., for image generation)
    """
    try:
        from arki_project.utils.token_counter import count_tokens
        token_count = count_tokens(input_text) + count_tokens(output_text) + extra_tokens
        if token_count <= 0:
            return

        from arki_project.database.connection import get_session
        from sqlalchemy import update
        from arki_project.database.models import User

        async with get_session() as session:
            await session.execute(
                update(User)
                .where(User.user_id == user_id)
                .values(tokens_used_today=User.tokens_used_today + token_count)
            )
            await session.commit()

        logger.debug("Token tracking: user=%d tokens=%d", user_id, token_count)
    except Exception as e:
        logger.debug("Token tracking error: %s", e)


async def check_token_budget(user_id: int) -> tuple[bool, int, int]:
    """Check if user has remaining token budget.

    Returns:
        (allowed, used_today, daily_budget)
    """
    try:
        from arki_project.database.connection import get_session
        from sqlalchemy import select
        from arki_project.database.models import User

        async with get_session() as session:
            result = await session.execute(
                select(User.tokens_used_today, User.daily_token_budget)
                .where(User.user_id == user_id)
            )
            row = result.first()
            if not row:
                return True, 0, 999_999_999  # Unknown user — allow
            used, budget = row[0] or 0, row[1] or 999_999_999
            return used < budget, used, budget
    except Exception as e:
        logger.debug("Budget check error: %s", e)
        return True, 0, 999_999_999  # On error — allow


