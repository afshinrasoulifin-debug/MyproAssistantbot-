
from __future__ import annotations
"""
utils/ai_client_domains/request_builder.py — Request Builder
═════════════════════════════════════════════════════════════
Build and validate API request payloads.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def build_request_payload(
    provider: str,
    model: str,
    messages: List[Dict[str, str]],
    system_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    tools: Optional[list] = None,
) -> Dict[str, Any]:
    """Build normalized request payload for any provider."""
    if provider == "gemini":
        return _build_gemini(model, messages, system_prompt, temperature, max_tokens, tools)
    else:
        return _build_openai_format(model, messages, system_prompt, temperature, max_tokens)


def _build_gemini(model: str, messages: list, system_prompt: str, temperature: float, max_tokens: int, tools: Any) -> Any:
    contents = []
    for msg in messages:
        role = "user" if msg.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    body = {
        "contents": contents,
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if system_prompt:
        body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    if tools:
        body["tools"] = tools
    return body


def _build_openai_format(model: str, messages: list, system_prompt: str, temperature: float, max_tokens: int) -> Any:
    msgs = list(messages)
    if system_prompt:
        msgs.insert(0, {"role": "system", "content": system_prompt})
    return {
        "model": model,
        "messages": msgs,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


