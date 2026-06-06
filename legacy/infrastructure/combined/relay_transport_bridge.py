
from __future__ import annotations
"""
RelayTransportBridge — Combines relay + transport + bridge.
"""
import logging
from typing import Callable, Dict



logger = logging.getLogger(__name__)

class RelayTransportBridge:
    """Bridge different transports with relay capabilities."""

    def __init__(self) -> None:
        self._transports: Dict[str, Callable] = {}
        self._relays: Dict[str, str] = {}

    def add_transport(self, name: str, handler: Callable) -> None:
        self._transports[name] = handler

    def add_relay(self, source: str, target: str) -> None:
        self._relays[source] = target

    async def send(self, transport: str, message: dict) -> dict:
        # Check if relay needed
        target = self._relays.get(transport, transport)
        handler = self._transports.get(target)
        if handler:
            return await handler(message)
        return {"error": f"Transport {target} not found"}


