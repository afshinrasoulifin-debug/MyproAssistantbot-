
from __future__ import annotations
"""InfraServiceBus — Service-to-service communication bus."""
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List



logger = logging.getLogger(__name__)

class InfraServiceBus:
    def __init__(self) -> None:
        self._services: Dict[str, Callable] = {}
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)

    def register_service(self, name: str, handler: Callable) -> None:
        self._services[name] = handler

    def listen(self, service: str, handler: Callable) -> Any:
        self._listeners[service].append(handler)

    async def call(self, service: str, data: Any = None) -> Any:
        handler = self._services.get(service)
        if not handler:
            raise ValueError(f"Service not found: {service}")
        result = await handler(data)
        for listener in self._listeners.get(service, []):
            try:
                await listener(result)
            except Exception as _exc:
                logger.debug("Suppressed: %s", _exc)
        return result


