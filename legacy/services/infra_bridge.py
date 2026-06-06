
from __future__ import annotations
"""
services/infra_bridge.py — Services ↔ Infrastructure Bridge
═══════════════════════════════════════════════════════════
Provides infrastructure access to service layer.
"""

import logging
from typing import Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class ServiceInfraBridge:
    """Bridge between services and infrastructure layer."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._infra = None
        return cls._instance

    @property
    def infra(self):
        if self._infra is None:
            try:
                from arki_project.core.boot import get_infra
                self._infra = get_infra()
            except ImportError as _exc:
                logger.debug("Suppressed: %s", _exc)
        return self._infra

    @property
    def registry(self):
        return self.infra["registry"] if self.infra else None

    @property
    def event_bus(self):
        return self.infra.get("event_bus") if self.infra else None

    def get_component(self, name: str) -> Any:
        reg = self.registry
        return reg.get(name) if reg else None

    async def emit(self, event: str, data: Any = None):
        bus = self.event_bus
        if bus:
            await bus.emit(f"service.{event}", data)


def get_service_bridge() -> ServiceInfraBridge:
    return ServiceInfraBridge()


