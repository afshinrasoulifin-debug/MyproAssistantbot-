
from __future__ import annotations
"""
tg_bot/middlewares/tracing_middleware.py — Request Tracing v10.4.0
═══════════════════════════════════════════════════════════════════
v10.4.0: Integrates DistributedTracer + SLATracker + ErrorAggregator
for deep observability across the entire request pipeline.

Each request gets:
  - A unique trace_id
  - A root Span tracked by DistributedTracer
  - Latency recorded in SLATracker
  - Errors recorded in ErrorAggregator
"""
import logging
import os
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)


def _generate_trace_id() -> str:
    """Generate a cryptographically random trace ID."""
    return os.urandom(8).hex()


def _get_tracer() -> None:
    try:
        from arki_project.utils.titanium import get_distributed_tracer
        return get_distributed_tracer()
    except Exception:
        return None


def _get_sla() -> None:
    try:
        from arki_project.utils.titanium import get_sla_tracker
        return get_sla_tracker()
    except Exception:
        return None


def _get_aggregator() -> None:
    try:
        from arki_project.utils.titanium import get_error_aggregator
        return get_error_aggregator()
    except Exception:
        return None


class TracingMiddleware(BaseMiddleware):
    """
    Deep tracing middleware with full TITANIUM integration.
    
    Provides:
      - data["trace_id"]    → str (unique per request)
      - data["trace_start"] → float (monotonic timestamp)
      - data["trace_span"]  → Span (root span for sub-span creation)
    
    Integrates:
      - DistributedTracer: creates root span per request
      - SLATracker: records latency for SLA compliance
      - ErrorAggregator: records errors with context
    """

    def __init__(self) -> None:
        self._total_requests = 0
        self._total_time_ms = 0.0
        self._slow_requests = 0  # > 5s
        self._errors = 0

    @property
    def stats(self) -> Dict[str, Any]:
        avg = self._total_time_ms / max(1, self._total_requests)
        return {
            "total_requests": self._total_requests,
            "avg_latency_ms": round(avg, 2),
            "slow_requests": self._slow_requests,
            "errors": self._errors,
        }

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        trace_id = _generate_trace_id()
        start = time.monotonic()
        self._total_requests += 1

        # Inject trace context
        data["trace_id"] = trace_id
        data["trace_start"] = start

        # v10.4.0: Start distributed trace span
        tracer = _get_tracer()
        root_span = None
        if tracer:
            user_id = getattr(getattr(event, "from_user", None), "id", 0)
            event_type = type(event).__name__
            root_span = tracer.start_trace(f"request:{event_type}:u{user_id}")
            data["trace_span"] = root_span

        user_id = getattr(getattr(event, "from_user", None), "id", 0)
        event_type = type(event).__name__

        logger.debug("[%s] START %s user=%d", trace_id, event_type, user_id)

        try:
            result = await handler(event, data)
            elapsed_ms = (time.monotonic() - start) * 1000
            self._total_time_ms += elapsed_ms

            # v10.4.0: Finish span + SLA tracking
            if root_span and tracer:
                tracer.finish_span(root_span, status="ok")
            sla = _get_sla()
            if sla:
                sla.record_check(success=True, latency_ms=elapsed_ms, provider="telegram_handler")

            if elapsed_ms > 5000:
                self._slow_requests += 1
                logger.warning(
                    "[%s] SLOW %s user=%d %.0fms",
                    trace_id, event_type, user_id, elapsed_ms,
                )
            else:
                logger.debug(
                    "[%s] END %s user=%d %.0fms",
                    trace_id, event_type, user_id, elapsed_ms,
                )
            return result
        except Exception as exc:
            self._errors += 1
            elapsed_ms = (time.monotonic() - start) * 1000
            self._total_time_ms += elapsed_ms

            # v10.4.0: Record error in span + aggregator
            if root_span and tracer:
                tracer.finish_span(root_span, status="error")
            agg = _get_aggregator()
            if agg:
                agg.record(exc, context=f"handler:{event_type}")
            sla = _get_sla()
            if sla:
                sla.record_check(success=False, latency_ms=elapsed_ms, provider="telegram_handler")

            logger.error(
                "[%s] ERROR %s user=%d %.0fms: %s",
                trace_id, event_type, user_id, elapsed_ms, exc,
            )
            raise


# v10.4.1: Wire observability layer into tracing
def _get_observability() -> None:
    try:
        from arki_project.core.observability import get_observability
        return get_observability()
    except Exception:
        return None


def _wire_observability_to_tracing() -> None:
    """Auto-wire observability metrics into every request.
    Called once during boot to register metric recording hooks.
    """
    obs = _get_observability()
    if not obs:
        return
    # Record key metrics
    obs.metrics.set_gauge("system.booted", 1)
    logger.info("Observability wired into tracing middleware")
    return obs


