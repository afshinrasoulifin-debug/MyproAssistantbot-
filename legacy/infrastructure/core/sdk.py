
from __future__ import annotations
"""ArkiSDK — Public SDK for Arki Engine integration."""
import logging
from typing import Any



logger = logging.getLogger(__name__)

class ArkiSDK:
    """Arki Engine SDK — programmatic access to all features."""

    def __init__(self) -> None:
        self._components: dict = {}
        self.version = "9.8.2"

    def register(self, name: str, component: Any) -> Any:
        self._components[name] = component

    def get(self, name: str) -> Any:
        return self._components.get(name)

    async def chat(self, message: str, user_id: int = 0, model: str = "") -> str:
        client = self._components.get("ai_client")
        if client:
            return await client.ask(message, user_id=user_id, model=model)
        return ""

    async def search(self, query: str) -> list:
        searcher = self._components.get("search")
        if searcher:
            return await searcher.search(query)
        return []


