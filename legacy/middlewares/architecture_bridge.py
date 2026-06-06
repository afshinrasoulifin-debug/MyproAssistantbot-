
from __future__ import annotations
"""
tg_bot/middlewares/architecture_bridge.py
Bridges 13-layer architecture to handler execution.
"""
import logging
import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)


class ArchitectureBridgeMiddleware(BaseMiddleware):
    """
    Bridges the 13-layer architecture to every handler call.
    Emits events, tracks metrics, enables architecture features.
    """

    def __init__(self, arch_registry=None):
        self._registry = arch_registry

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Inject architecture registry
        data["arch_registry"] = self._registry

        # Track timing
        start = time.monotonic()
        try:
            result = await handler(event, data)
            return result
        finally:
            elapsed_ms = (time.monotonic() - start) * 1000

            # Emit to EventBus
            try:
                from arki_project.core.arch_events import emit_handler_event
                tg_user = getattr(event, "from_user", None)
                user_id = tg_user.id if tg_user else None  # v9.8.7: None not 0 for no-user events
                import asyncio
                asyncio.create_task(
                    emit_handler_event("middleware", user_id, {
                        "latency_ms": elapsed_ms,
                    })
                )
            except Exception as _exc:
                logger.debug("Suppressed: %s", _exc)


