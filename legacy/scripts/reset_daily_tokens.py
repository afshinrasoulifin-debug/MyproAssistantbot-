
"""
scripts/reset_daily_tokens.py — Reset tokens_used_today for all users.
Run daily via cron: 0 0 * * * python scripts/reset_daily_tokens.py
"""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def reset_tokens():
    from arki_project.database.connection import get_session
    from sqlalchemy import update
    from arki_project.database.models import User

    async with get_session() as session:
        result = await session.execute(
            update(User).values(tokens_used_today=0)
        )
        await session.commit()
        logger.info("Reset tokens_used_today for %d users", result.rowcount)


if __name__ == "__main__":
    asyncio.run(reset_tokens())


