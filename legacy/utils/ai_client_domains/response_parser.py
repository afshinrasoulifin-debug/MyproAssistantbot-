
from __future__ import annotations
"""
utils/ai_client_domains/response_parser.py — Response Parsing
══════════════════════════════════════════════════════════════
Parse, validate, and normalize AI provider responses.
"""

import logging
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)


def parse_ai_response(provider: str, data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Parse raw API response into (text, metadata)."""
    if provider == "gemini":
        return _parse_gemini(data)
    elif provider in ("groq", "openrouter"):
        return _parse_openai_format(data)
    return str(data), {}

def _parse_gemini(data: Dict) -> Tuple[str, Dict]:
    meta = {}
    candidates = data.get("candidates", [])
    if not candidates:
        error = data.get("error", {})
        return f"Error: {error.get('message', 'No candidates')}", {"error": True}

    first = candidates[0]
    parts = first.get("content", {}).get("parts", [])
    text = " ".join(p.get("text", "") for p in parts if "text" in p).strip()

    # Extract usage metadata
    usage = data.get("usageMetadata", {})
    if usage:
        meta["input_tokens"] = usage.get("promptTokenCount", 0)
        meta["output_tokens"] = usage.get("candidatesTokenCount", 0)

    meta["finish_reason"] = first.get("finishReason", "")
    return text, meta

def _parse_openai_format(data: Dict) -> Tuple[str, Dict]:
    meta = {}
    choices = data.get("choices", [])
    if not choices:
        error = data.get("error", {})
        return f"Error: {error.get('message', 'No choices')}", {"error": True}

    first = choices[0]
    text = first.get("message", {}).get("content", "").strip()

    usage = data.get("usage", {})
    if usage:
        meta["input_tokens"] = usage.get("prompt_tokens", 0)
        meta["output_tokens"] = usage.get("completion_tokens", 0)

    meta["finish_reason"] = first.get("finish_reason", "")
    meta["model"] = data.get("model", "")
    return text, meta

def validate_response(text: str, min_length: int = 1, max_length: int = 100000) -> bool:
    """Validate that response meets quality criteria."""
    if not text or len(text) < min_length:
        return False
    if len(text) > max_length:
        return False
    # Check for common error patterns
    error_patterns = ["Error:", "rate limit", "quota exceeded", "invalid api key"]
    for pattern in error_patterns:
        if text.lower().startswith(pattern.lower()):
            return False
    return True


