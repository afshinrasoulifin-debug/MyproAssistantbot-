
from __future__ import annotations
"""
tg_bot/middlewares/infrastructure_bridge.py — Infrastructure Bridge
v10.2: Bridges aiogram dispatcher with TITANIUM infrastructure layer.

Injects infrastructure services (HTTP pool, health monitor, AI orchestrator)
into handler data dict so handlers can access them without direct imports.
"""
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)

# Try to import TITANIUM components
try:
    from arki_project.utils.titanium import TITANIUM_VERSION
    from arki_project.utils.titanium.integration import shielded_get, shielded_post
    _TITANIUM_AVAILABLE = True
except ImportError:
    _TITANIUM_AVAILABLE = False


class InfrastructureBridgeMiddleware(BaseMiddleware):
    """
    Injects infrastructure references into handler data.
    
    Provides:
      - data["titanium_active"] → bool
      - data["shielded_get"] → async function
      - data["shielded_post"] → async function
      - data["infra_version"] → str
    """

    def __init__(self):
        self._request_count = 0

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "titanium_available": _TITANIUM_AVAILABLE,
            "requests_bridged": self._request_count,
        }

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        self._request_count += 1

        # Inject infrastructure into handler data
        data["titanium_active"] = _TITANIUM_AVAILABLE
        if _TITANIUM_AVAILABLE:
            data["shielded_get"] = shielded_get
            data["shielded_post"] = shielded_post
            data["infra_version"] = TITANIUM_VERSION
        else:
            data["infra_version"] = "legacy"

        return await handler(event, data)


