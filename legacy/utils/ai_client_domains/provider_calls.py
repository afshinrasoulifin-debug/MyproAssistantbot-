
from __future__ import annotations
"""
utils/ai_client_domains/provider_calls.py — Provider API Calls
═══════════════════════════════════════════════════════════════
Extracted from ai_client.py: each provider as a clean class.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseProvider:
    """Base class for AI provider API calls."""

    name: str = "base"
    base_url: str = ""

    def __init__(self, get_key_fn: Optional[Any]=None) -> None:
        self._get_key = get_key_fn

    async def _get_api_key(self) -> str:
        if self._get_key:
            key = await self._get_key(self.name)
            if key:
                return key
        return ""

    async def call(self, model: str, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

    def build_headers(self, api_key: str) -> Dict[str, str]:
        raise NotImplementedError


class GeminiProvider(BaseProvider):
    name = "gemini"
    base_url = "https://generativelanguage.googleapis.com/v1beta"

    def build_headers(self, api_key: str) -> Dict[str, str]:
        return {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    def build_body(self, model: str, messages: List[Dict],
                  temperature: float = 0.7, max_tokens: int = 8192,
                  system_prompt: str = "", tools: list = None) -> Dict:
        contents = []
        for msg in messages:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_prompt:
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        if tools:
            body["tools"] = tools
        return body


class GroqProvider(BaseProvider):
    name = "groq"
    base_url = "https://api.groq.com/openai/v1"

    def build_headers(self, api_key: str) -> Dict[str, str]:
        return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def build_body(self, model: str, messages: List[Dict],
                  temperature: float = 0.7, max_tokens: int = 4096,
                  system_prompt: str = "") -> Dict:
        msgs = list(messages)
        if system_prompt:
            msgs.insert(0, {"role": "system", "content": system_prompt})
        return {
            "model": model,
            "messages": msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }


class OpenRouterProvider(BaseProvider):
    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"

    def build_headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://arki-bot.com",
            "X-Title": "ARKI-Bot",
        }

    def build_body(self, model: str, messages: List[Dict],
                  temperature: float = 0.7, max_tokens: int = 4096,
                  system_prompt: str = "") -> Dict:
        msgs = list(messages)
        if system_prompt:
            msgs.insert(0, {"role": "system", "content": system_prompt})
        return {
            "model": model,
            "messages": msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }


