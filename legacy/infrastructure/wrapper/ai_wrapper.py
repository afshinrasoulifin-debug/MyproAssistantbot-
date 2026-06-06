
from __future__ import annotations
"""
AIWrapper — High-level wrapper combining gateway + provider + runtime.
One-call interface for all AI operations.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class AIWrapper:
    """Simplest possible interface: ask(prompt) → answer."""

    def __init__(self) -> None:
        self._gateway = None
        self._provider = None
        self._runtime = None
        self._history: List[Dict] = []

    def configure(self, gateway: Optional[Any]=None, provider: str=None, runtime: Optional[Any]=None) -> Any:
        self._gateway = gateway
        self._provider = provider
        self._runtime = runtime

    async def ask(self, prompt: str, model: str = "", user_id: int = 0, **kwargs) -> str:
        """One-call AI interface — handles routing, fallback, caching."""
        from arki_project.infrastructure.providers.base import ProviderRequest
        request = ProviderRequest(
            messages=[{"role": "user", "content": prompt}],
            model=model, user_id=user_id, **kwargs
        )
        if self._provider:
            resp = await self._provider.complete(request)
            return resp.content if resp.success else f"Error: {resp.error}"
        return "[AIWrapper] No provider configured"

    async def chat(self, messages: List[Dict], **kwargs) -> str:
        from arki_project.infrastructure.providers.base import ProviderRequest
        request = ProviderRequest(messages=messages, **kwargs)
        if self._provider:
            resp = await self._provider.complete(request)
            return resp.content if resp.success else f"Error: {resp.error}"
        return "[AIWrapper] No provider configured"


