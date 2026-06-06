
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
tg_bot/middlewares/analytics.py
───────────────────────────────
v29.0.0: Analytics middleware — tracks command usage,
response times, and errors for admin dashboards.
"""


import asyncio
import json
import logging
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from arki_project.database.connection import get_session
from arki_project.utils.alert_system import get_alert_system

# v10.3: Performance tracking
try:
    from arki_project.utils.performance_tracker import perf_tracker as _analytics_perf
except ImportError:
    _analytics_perf = None
from arki_project.utils.metrics_collector import get_metrics
from arki_project.database.models import AnalyticsEvent

logger = logging.getLogger(__name__)


class AnalyticsMiddleware(BaseMiddleware):
    """
    Tracks every handler invocation for analytics.

    Records:
      • Command name or callback action
      • Response time (ms)
      • Success/failure
      • User ID and timestamp
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not self._enabled:
            return await handler(event, data)

        tg_user = data.get("event_from_user")
        user_id = tg_user.id if tg_user else 0

        # Determine event type and command
        event_type = "message"
        command = ""

        # Handle Update wrapper → extract actual event
        from aiogram.types import Update
        actual = event
        if isinstance(event, Update):
            actual = event.message or event.callback_query or event

        if isinstance(actual, Message):
            text = actual.text or ""
            if text.startswith("/"):
                event_type = "command"
                command = text.split()[0].split("@")[0] if text else ""
            elif actual.document:
                event_type = "document"
            elif actual.photo:
                event_type = "photo"
            elif actual.voice:
                event_type = "voice"
            elif actual.sticker:
                event_type = "sticker"
        elif isinstance(actual, CallbackQuery):
            event_type = "callback"
            command = actual.data or ""

        # Execute handler and measure time
        start_time = time.monotonic()
        error_msg = ""
        success = True

        try:
            result = await handler(event, data)
            return result
        except HandlerError as exc:
            success = False
            error_msg = f"{type(exc).__name__}: {str(exc)[:500]}"
            # v9.1: Alert on errors
            try:
                asyncio.create_task(
                    get_alert_system().error(
                        f"Handler Error: {command or event_type}",
                        f"User: {user_id}\n{error_msg[:300]}"
                    )
                )
            except HandlerError as _exc:
                logger.debug("Suppressed: %s", _exc)
            raise
        finally:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            # v10.3: Feed performance tracker
            if _analytics_perf:
                try:
                    op_name = command or event_type or "unknown"
                    _analytics_perf._timings[op_name].append(elapsed_ms / 1000)
                    _analytics_perf._counts[op_name] += 1
                    if not success:
                        _analytics_perf._errors[op_name] += 1
                    # v10.3.1: Track total middleware pipeline time
                    _analytics_perf._timings["_middleware_total"].append(elapsed_ms / 1000)
                    _analytics_perf._counts["_middleware_total"] += 1
                except HandlerError as _err:
                    logger.warning("Suppressed error: %s", _err)

            # v9.1: Collect metrics
            _metrics = get_metrics()
            _metrics.increment("messages_total", labels={"type": event_type})
            _metrics.observe("response_time_ms", elapsed_ms, labels={"type": event_type})
            if not success:
                _metrics.increment("errors_total", labels={"type": event_type})

            # v10.4: True fire-and-forget via background task
            # DB write NEVER blocks the response pipeline
            async def _persist_analytics():
                try:
                    async with get_session() as session:
                        session.add(AnalyticsEvent(
                            user_id=user_id,
                            event_type=event_type,
                            command=command[:64],
                            response_time_ms=elapsed_ms,
                            success=success,
                            error_message=error_msg,
                            metadata_json=json.dumps({
                                "chat_id": getattr(
                                    getattr(event, "chat", None), "id", 0
                                ),
                            }),
                        ))
                except HandlerError as db_exc:
                    logger.debug("Analytics write failed: %s", db_exc)

            try:
                asyncio.create_task(_persist_analytics())
            except RuntimeError:
                pass  # No event loop (shouldn't happen in production)


