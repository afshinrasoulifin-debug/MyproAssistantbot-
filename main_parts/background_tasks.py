
"""main_parts/background_tasks.py — Daily token reset loop + task error callback."""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

async def _daily_token_reset_loop() -> None:
    """Reset tokens_used_today at midnight UTC every day."""
    import asyncio
    from datetime import datetime, timezone, timedelta
    while True:
        now = datetime.now(timezone.utc)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_secs = (midnight - now).total_seconds()
        await asyncio.sleep(wait_secs)
        try:
            from arki_project.database.connection import get_session
            from sqlalchemy import update
            from arki_project.database.models import User
            async with get_session() as session:
                await session.execute(update(User).values(tokens_used_today=0))
                await session.commit()
            logger.info("Daily token reset complete")
        except ArkiBaseError as e:
            logger.error("Token reset failed: %s", e)


# ── v9 Intelligence Module System ──
from arki_project.core.init_modules import startup_modules, shutdown_modules
from arki_project.utils.v7_core import persist_memory

# Version from config (reads VERSION file)
try:
    from config import APP_VERSION as _VERSION
except ImportError:
    _VERSION = "29.0.0"

# ── v9 Enterprise Architecture Layer ──
try:
    from arki_project.architecture.setup import boot_architecture
except ImportError:
    boot_architecture = None


# Token reset task is started in main()
def _task_error_callback(task: asyncio.Task) -> None:
    """Log unhandled exceptions from background tasks."""
    try:
        exc = task.exception()
    except asyncio.CancelledError:
        return
    if exc:
        logger.error("Background task %s crashed: %s", task.get_name(), exc, exc_info=exc)




