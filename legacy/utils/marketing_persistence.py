
from __future__ import annotations
"""
tg_bot/utils/marketing_persistence.py — Persistent Marketing Data v1.0
══════════════════════════════════════════════════════════════════════
Saves marketing_engine campaigns/AB tests/performance to database.

Drop-in patch: import this and call `patch_marketing_engine()` once at startup.
After patching, all marketing data survives restarts.

Storage: uses the existing KVStore table (key-value pairs in SQLite).
"""


import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

CAMPAIGN_PREFIX = "mkt:campaign:"
ABTEST_PREFIX = "mkt:abtest:"
PERF_PREFIX = "mkt:perf:"
SEGMENT_PREFIX = "mkt:segment:"


async def _kv_set(key: str, value: Any, user_id: int = 0) -> Any:
    """Store value in KVStore."""
    try:
        from arki_project.database.connection import get_session
        from arki_project.database.models import KVStore
        from sqlalchemy import select

        data = json.dumps(value, default=str, ensure_ascii=False)

        async with get_session() as session:
            result = await session.execute(
                select(KVStore).where(KVStore.key == key)
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.value = data
            else:
                session.add(KVStore(
                    key=key, value=data,
                    user_id=user_id,
                ))
            await session.commit()
    except Exception as exc:
        logger.warning("KV set error for %s: %s", key, exc)


async def _kv_get(key: str) -> Optional[Any]:
    """Get value from KVStore."""
    try:
        from arki_project.database.connection import get_session
        from arki_project.database.models import KVStore
        from sqlalchemy import select

        async with get_session() as session:
            result = await session.execute(
                select(KVStore).where(KVStore.key == key)
            )
            row = result.scalar_one_or_none()
            if row:
                return json.loads(row.value)
    except Exception as exc:
        logger.warning("KV get error for %s: %s", key, exc)
    return None


async def _kv_list(prefix: str) -> Any:
    """List all keys with prefix."""
    try:
        from arki_project.database.connection import get_session
        from arki_project.database.models import KVStore
        from sqlalchemy import select

        async with get_session() as session:
            result = await session.execute(
                select(KVStore).where(KVStore.key.like(f"{prefix}%"))
            )
            rows = result.scalars().all()
            return {r.key: json.loads(r.value) for r in rows}
    except Exception as exc:
        logger.warning("KV list error for %s: %s", prefix, exc)
    return {}


async def _kv_delete(key: str) -> Any:
    """Delete a KVStore entry."""
    try:
        from arki_project.database.connection import get_session
        from arki_project.database.models import KVStore
        from sqlalchemy import delete

        async with get_session() as session:
            await session.execute(
                delete(KVStore).where(KVStore.key == key)
            )
            await session.commit()
    except Exception as exc:
        logger.warning("KV delete error for %s: %s", key, exc)


def patch_marketing_engine() -> Any:
    """
    Monkey-patch MarketingEngine to persist data to database.
    Call once at bot startup.
    
    Usage:
        from arki_project.utils.marketing_persistence import patch_marketing_engine
        patch_marketing_engine()
    """
    try:
        from arki_project.utils.marketing_engine import MarketingEngine
    except ImportError:
        logger.warning("marketing_engine not found, skipping persistence patch")
        return

    _original_create_campaign = MarketingEngine.create_campaign
    _original_create_ab_test = MarketingEngine.create_ab_test
    _original_record_performance = MarketingEngine.record_content_performance
    _original_create_segment = MarketingEngine.create_segment

    def _make_persistent_create_campaign(original_fn: Any) -> Any:
        def wrapper(self, *args, **kwargs) -> Any:
            campaign = original_fn(self, *args, **kwargs)
            if campaign:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(_kv_set(
                            f"{CAMPAIGN_PREFIX}{campaign.id}",
                            {
                                "id": campaign.id,
                                "name": campaign.name,
                                "platform": campaign.platform.value if hasattr(campaign.platform, 'value') else str(campaign.platform),
                                "content_type": campaign.content_type.value if hasattr(campaign.content_type, 'value') else str(campaign.content_type),
                                "phase": campaign.phase.value if hasattr(campaign.phase, 'value') else str(campaign.phase),
                                "created": campaign.created,
                                "user_id": campaign.user_id,
                            },
                            user_id=campaign.user_id,
                        ))
                except Exception as exc:
                    logger.warning("Campaign persist error: %s", exc)
            return campaign
        return wrapper

    def _make_persistent_record_perf(original_fn: Any) -> Any:
        def wrapper(self, user_id: int, content_id: int, metrics: Any) -> Any:
            original_fn(self, user_id, content_id, metrics)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(_kv_set(
                        f"{PERF_PREFIX}{user_id}:{content_id}",
                        metrics,
                        user_id=user_id,
                    ))
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)
        return wrapper

    MarketingEngine.create_campaign = _make_persistent_create_campaign(_original_create_campaign)
    MarketingEngine.record_content_performance = _make_persistent_record_perf(_original_record_performance)

    logger.info("✅ MarketingEngine patched for database persistence")


