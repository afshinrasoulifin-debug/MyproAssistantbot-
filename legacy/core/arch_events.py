
from __future__ import annotations
"""
tg_bot/core/arch_events.py — Architecture Event Integration
═══════════════════════════════════════════════════════════
Bridge between handler layer and architecture EventBus.
Emits events for telemetry, monitoring, and smart routing.

v9.0: Connects the 13-layer architecture to actual bot operations.
"""


import logging
import time
from typing import Any, Dict, Optional

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

# Global reference to architecture registry (set during boot)
_registry: Optional[Dict[str, Any]] = None


def set_registry(registry: Dict[str, Any]) -> None:
    """Set the architecture registry reference. Called from main.py after boot."""
    global _registry
    _registry = registry
    logger.info("Architecture event bridge connected (%d components)", len(registry))


def get_event_bus() -> Any:
    """Get the EventBus from registry."""
    if _registry:
        return _registry.get("event_bus")
    return None


def get_smart_engine() -> Any:
    """Get the SmartEngine for adaptive parameter tuning."""
    if _registry:
        return _registry.get("smart_engine")
    return None


def get_performance_engine() -> Any:
    """Get the PerformanceEngine for response time tracking."""
    if _registry:
        return _registry.get("performance_engine")
    return None


async def emit_event(topic: str, payload: Dict[str, Any]) -> None:
    """Emit an event to the architecture EventBus (fire-and-forget)."""
    bus = get_event_bus()
    if bus:
        try:
            await bus.publish(topic, payload)
        except Exception as e:
            logger.debug("Event emit failed (%s): %s", topic, e)


async def emit_handler_start(handler_name: str, user_id: int) -> float:
    """Emit handler.start event, return start timestamp."""
    t0 = time.time()
    await emit_event("handler.start", {
        "handler": handler_name,
        "user_id": user_id,
        "time": t0,
    })
    return t0


async def emit_handler_complete(
    handler_name: str, user_id: int, start_time: float, success: bool = True
) -> None:
    """Emit handler.complete event with timing."""
    duration = time.time() - start_time
    await emit_event("handler.complete", {
        "handler": handler_name,
        "user_id": user_id,
        "duration_s": duration,
        "success": success,
    })
    
    # Update SmartEngine user profile
    smart = get_smart_engine()
    if smart:
        try:
            smart.update_user(user_id, last_handler=handler_name)
        except Exception as e:
            logger.debug("Suppressed: %s", e)

    # Track in PerformanceEngine
    perf = get_performance_engine()
    if perf:
        try:
            perf.record(handler_name, duration)
        except Exception as e:
            logger.debug("Suppressed: %s", e)


async def emit_ai_request(model: str, user_id: int, tokens_est: int = 0) -> None:
    """Emit AI request event for tracking model usage."""
    await emit_event("ai.request", {
        "model": model,
        "user_id": user_id,
        "tokens_est": tokens_est,
        "time": time.time(),
    })


async def emit_ai_response(
    model: str, user_id: int, duration_s: float, success: bool = True
) -> None:
    """Emit AI response event."""
    await emit_event("ai.response", {
        "model": model,
        "user_id": user_id,
        "duration_s": duration_s,
        "success": success,
    })


async def emit_pipeline_classify(
    user_id: int, category: str, complexity: str, confidence: float
) -> None:
    """Emit pipeline classification event."""
    await emit_event("pipeline.classify", {
        "user_id": user_id,
        "category": category,
        "complexity": complexity,
        "confidence": confidence,
    })


async def emit_search(user_id: int, query: str, results_count: int = 0) -> None:
    """Emit search event."""
    await emit_event("search.query", {
        "user_id": user_id,
        "query": query[:100],
        "results_count": results_count,
    })


async def emit_marketing_action(
    action: str, user_id: int, details: Dict[str, Any] = None
) -> None:
    """Emit marketing/sales automation event."""
    await emit_event("marketing.action", {
        "action": action,
        "user_id": user_id,
        "details": details or {},
        "time": time.time(),
    })


# ── v9.1: Convenience functions for handler integration ──

async def emit_handler_event(handler_name: str, user_id: int, data: dict = None) -> None:
    """Emit a handler execution event to the architecture EventBus."""
    await emit_event("handler.executed", {
        "handler": handler_name,
        "user_id": user_id,
        **(data or {}),
    })

async def emit_ai_event(model: str, tokens: int, user_id: int, latency_ms: float) -> None:
    """Emit an AI model call event."""
    await emit_event("ai.call", {
        "model": model,
        "tokens": tokens,
        "user_id": user_id,
        "latency_ms": latency_ms,
    })

async def emit_error_event(source: str, error: str, user_id: int = 0) -> None:
    """Emit an error event."""
    await emit_event("error.occurred", {
        "source": source,
        "error": error[:500],
        "user_id": user_id,
    })


