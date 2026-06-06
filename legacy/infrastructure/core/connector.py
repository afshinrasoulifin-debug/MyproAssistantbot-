
from __future__ import annotations
"""Connector — Connect to external services."""
import logging
from typing import Dict, Any



logger = logging.getLogger(__name__)

class ConnectorConfig:
    def __init__(self, name: str, url: str, key: str = "") -> None:
        self.name = name
        self.url = url
        self.key = key

class Connector:
    """Universal service connector."""

    def __init__(self) -> None:
        self._connections: Dict[str, ConnectorConfig] = {}
        self._active: Dict[str, bool] = {}

    def add(self, config: ConnectorConfig) -> Any:
        self._connections[config.name] = config
        self._active[config.name] = True

    async def connect(self, name: str) -> bool:
        if name in self._connections:
            self._active[name] = True
            return True
        return False

    async def disconnect(self, name: str) -> Any:
        self._active[name] = False

    def is_connected(self, name: str) -> bool:
        return self._active.get(name, False)


