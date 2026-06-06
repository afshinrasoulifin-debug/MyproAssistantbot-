
from __future__ import annotations
"""
AutoProvider — Zero-config provider that auto-discovers and configures itself.
"""
import os, logging
from typing import Dict, Any
from arki_project.infrastructure.providers.base import BaseProvider, ProviderRequest, ProviderResponse
from arki_project.infrastructure.providers.fallback_provider import FallbackProvider



logger = logging.getLogger(__name__)

class AutoProvider(BaseProvider):
    """Auto-detect available API keys and configure optimal provider chain."""

    def __init__(self) -> None:
        super().__init__("auto", priority=99)
        self._chain = FallbackProvider()
        self._discovered: Dict[str, str] = {}

    def discover(self) -> Any:
        keys = {
            "gemini": os.environ.get("GEMINI_API_KEY") or os.environ.get("AI_API_KEY", ""),
            "groq": os.environ.get("GROQ_API_KEY", ""),
            "openrouter": os.environ.get("OPENROUTER_API_KEY", ""),
            "openai": os.environ.get("OPENAI_API_KEY", ""),
            "anthropic": os.environ.get("ANTHROPIC_API_KEY", ""),
        }
        self._discovered = {k: v for k, v in keys.items() if v.strip()}
        logger.info("AutoProvider discovered: %s", list(self._discovered.keys()))
        return self._discovered

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        if not self._chain._chain:
            self.discover()
        return await self._chain.complete(request)


