
from __future__ import annotations
"""
UnifiedClient — Single client interface for all AI providers.
"""
import logging
from typing import Any, Dict



logger = logging.getLogger(__name__)

class UnifiedClient:
    """One client to rule them all — abstracts Gemini, Groq, OpenRouter, OpenAI."""

    def __init__(self) -> None:
        self._providers: Dict[str, Any] = {}
        self._default_provider: str = "gemini"
        self._request_count = 0

    def register_provider(self, name: str, client: Any) -> None:
        self._providers[name] = client

    async def complete(self, messages: list, model: str = "", **kwargs) -> dict:
        self._request_count += 1
        provider = self._resolve_provider(model)
        client = self._providers.get(provider)
        if not client:
            return {"error": f"Provider {provider} not configured", "success": False}
        try:
            return await client.complete(messages, model=model, **kwargs)
        except Exception as e:
            return {"error": str(e), "success": False}

    def _resolve_provider(self, model: str) -> str:
        if "gemini" in model: return "gemini"
        if "llama" in model or "groq" in model: return "groq"
        if "/" in model: return "openrouter"
        return self._default_provider


