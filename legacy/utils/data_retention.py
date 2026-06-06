
from __future__ import annotations
"""
tg_bot/utils/data_retention.py — Data Retention Automation v9.4
Automatically purge old data based on retention policies.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

RETENTION_POLICIES = {
    "chat_messages": 90,     # days
    "analytics_events": 365,
    "pipeline_logs": 30,
    "telemetry_metrics": 30,
    "audit_entries": 730,    # 2 years for compliance
    "token_usage": 365,
}


async def run_retention_cleanup(session_factory: Any) -> Dict[str, int]:
    """Run data retention cleanup based on policies."""
    from arki_project.database.models import (
        ChatMessage, AnalyticsEvent, PipelineLog, TelemetryMetric
    )
    results = {}

    table_map = {
        "chat_messages": ChatMessage,
        "analytics_events": AnalyticsEvent,
        "pipeline_logs": PipelineLog,
        "telemetry_metrics": TelemetryMetric,
    }

    async with session_factory() as session:
        for table_name, days in RETENTION_POLICIES.items():
            model = table_map.get(table_name)
            if not model:
                continue
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            try:
                from sqlalchemy import delete
                created_col = getattr(model, 'created_at', None) or getattr(model, 'timestamp', None)
                if created_col is not None:
                    stmt = delete(model).where(created_col < cutoff)
                    result = await session.execute(stmt)
                    results[table_name] = result.rowcount
                    logger.info("Retention: deleted %d rows from %s (older than %d days)",
                               result.rowcount, table_name, days)
            except Exception as e:
                logger.error("Retention cleanup failed for %s: %s", table_name, e)
                results[table_name] = -1

        await session.commit()

    return results


_retention_instance = None

def get_retention_manager() -> Any:
    """Get or create the global DataRetention manager."""
    global _retention_instance
    if _retention_instance is None:
        _retention_instance = DataRetention()
    return _retention_instance


