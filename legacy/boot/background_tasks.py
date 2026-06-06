
from __future__ import annotations
"""
boot/background_tasks.py — Background task setup for Arki Engine v29.0.0
═══════════════════════════════════════════════════════════════════════════
Extracted from main.py for clarity.
"""

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def start_background_tasks(settings: dict, bot: Optional[Any]=None, ai_client: Optional[Any]=None) -> list:
    """Start all background tasks and return the task list."""
    tasks = []
    
    background_tasks: list[asyncio.Task] = []

    # 9a. Cleanup old messages (every 24h)
    async def cleanup_old_messages() -> None:
        """Delete chat_messages older than 30 days every 24h."""
        while True:
            await asyncio.sleep(86400)
            try:
                cutoff = datetime.now(timezone.utc) - timedelta(days=30)
                async with get_session() as session:
                    result = await session.execute(
                        delete(DBChatMessage).where(
                            DBChatMessage.created_at < cutoff,
                        ),
                    )
                    await session.commit()
                    count = result.rowcount  # type: ignore[union-attr]
                if count:
                    logger.info("Cleaned up %d old messages (>30 days)", count)
            except Exception as e:
                logger.warning("Message cleanup failed: %s", e)

    _t = asyncio.create_task(cleanup_old_messages(), name="cleanup_old_messages")
    _t.add_done_callback(_task_error_callback)
    background_tasks.append(_t)

    # 9b. Periodic in-memory cache eviction (every hour)
    async def evict_stale_memory() -> None:
        """Evict inactive user conversations from memory every hour."""
        while True:
            await asyncio.sleep(3600)
            try:
                evicted = ai_client.evict_stale_users(max_age_seconds=3600)
                if evicted:
                    logger.info("♻️ Evicted %d stale user histories", evicted)
            except Exception as e:
                logger.warning("Memory eviction failed: %s", e)

    _t = asyncio.create_task(evict_stale_memory(), name="evict_stale_memory")
    _t.add_done_callback(_task_error_callback)
    background_tasks.append(_t)

    # 9c. Analytics cleanup (every 24h — keep 90 days)
    async def cleanup_analytics() -> None:
        """Delete analytics events older than 90 days."""
        while True:
            await asyncio.sleep(86400)
            try:
                from arki_project.database.models import AnalyticsEvent
                cutoff = datetime.now(timezone.utc) - timedelta(days=90)
                async with get_session() as session:
                    result = await session.execute(
                        delete(AnalyticsEvent).where(
                            AnalyticsEvent.created_at < cutoff,
                        ),
                    )
                    await session.commit()
                    count = result.rowcount  # type: ignore[union-attr]
                if count:
                    logger.info("Cleaned up %d old analytics events (>90 days)", count)
            except Exception as e:
                logger.warning("Analytics cleanup failed: %s", e)

    _t = asyncio.create_task(cleanup_analytics(), name="cleanup_analytics")
    _t.add_done_callback(_task_error_callback)
    background_tasks.append(_t)

    # v8: Persist memory every 5 minutes
    async def _v8_persist() -> None:
        while True:
            await asyncio.sleep(300)
            try:
                await persist_memory()
            except Exception as e:
                logger.debug("Suppressed: %s", e)
    _t = asyncio.create_task(_v8_persist(), name="_v8_persist")
    _t.add_done_callback(_task_error_callback)
    background_tasks.append(_t)

    # 9d. Recover pending reminders from DB
    try:
        from arki_project.handlers.automation import recover_reminders
        recovered = await recover_reminders(bot)
        if recovered:
            logger.info("♻️ Recovered %d pending reminders", recovered)
    except Exception as e:
        logger.warning("Reminder recovery failed: %s", e)

    # 9e. Start monitor background checker
    monitor_task = None
    try:
        from arki_project.handlers.agents import start_monitor_bg
        monitor_task = await start_monitor_bg(bot)
        if monitor_task:
            background_tasks.append(monitor_task)
        logger.info("♻️ Monitor background checker started (hourly)")
    except Exception as e:
        logger.warning("Monitor background start failed: %s", e)

    # ── 9f. AutoRun Engine (v9) ──
    try:
        from arki_project.utils.v7_core import get_autorun_engine
        _autorun = get_autorun_engine()
        # v10.3.1: Register degradation auto-recovery task
        try:
            from arki_project.core.autorun import register_recovery_task
            register_recovery_task(_autorun)
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)
        await _autorun.start()
        logger.info('✅ AutoRun engine started (with auto-recovery)')
    except Exception as e:
        logger.warning('⚠️ AutoRun engine: %s', e)

    # ── 9g. Plugin System ──
    try:
        from arki_project.utils.plugin_system import PluginManager
        _plug = PluginManager()
        await _plug.discover('plugins')
        await _plug.start_all()
        logger.info('✅ Plugins: %d loaded', getattr(_plug, 'count', 0))
    except Exception as e:
        logger.debug('Plugin system: %s', e)

    # ── 9h. Degradation Manager ──
    try:
        _degradation = get_degradation_manager()
        _degradation.register_service('database')
        _degradation.register_service('ai_client')
        _degradation.register_service('telegram')
        _degradation.register_service('apex')
        _degradation.register_service('victor')  # v10.3: Victor Independent Intelligence
        logger.info('✅ Degradation manager initialized (5 services)')
    except Exception as e:
        logger.warning('⚠️ Degradation manager: %s', e)

    
    return tasks


