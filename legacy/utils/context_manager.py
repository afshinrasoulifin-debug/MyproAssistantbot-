
from __future__ import annotations
"""
tg_bot/utils/context_manager.py — Context Window Management v9.4
Token counting, history truncation, context compression.
"""
import logging
from typing import Dict, List, Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

# Approximate token limits per model
MODEL_LIMITS = {
    "gemini-2.5-pro": 1048576,
    "gemini-2.5-pro": 1048576,
    "llama-3.3-70b": 131072,
    "qwen-qwq-32b": 32768,
    "default": 32768,
}


def estimate_tokens(text: str) -> int:
    """Estimate token count (avg 4 chars per token for English, ~2 for Farsi)."""
    if not text:
        return 0
    # Quick heuristic: count chars, divide by average
    farsi_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    if farsi_chars > len(text) * 0.3:
        return len(text) // 2  # Farsi: ~2 chars per token
    return len(text) // 4  # English: ~4 chars per token


def get_model_limit(model: str) -> int:
    """Get token limit for a model."""
    for key, limit in MODEL_LIMITS.items():
        if key in model.lower():
            return limit
    return MODEL_LIMITS["default"]


class ContextWindowManager:
    """Manage conversation context within model limits."""

    def __init__(self, model: str = "gemini-2.5-pro", max_response_tokens: int = 65536192) -> None:
        self.model = model
        self.max_tokens = get_model_limit(model)
        self.max_response_tokens = max_response_tokens
        self.available_tokens = self.max_tokens - max_response_tokens

    def fit_messages(self, messages: List[Dict], system_prompt: str = "") -> List[Dict]:
        """Truncate message history to fit within context window."""
        system_tokens = estimate_tokens(system_prompt)
        budget = self.available_tokens - system_tokens

        if budget <= 0:
            return messages[-1:] if messages else []

        # Always keep the last message (current input)
        result = []
        running = 0

        # Work backward from most recent
        for msg in reversed(messages):
            content = msg.get("content", "") or msg.get("text", "")
            tokens = estimate_tokens(str(content))
            if running + tokens > budget:
                break
            result.insert(0, msg)
            running += tokens

        if len(result) < len(messages):
            logger.debug("Context truncated: %d → %d messages (%d tokens)",
                        len(messages), len(result), running)

        return result

    def compress_history(self, messages: List[Dict], keep_recent: int = 10) -> List[Dict]:
        """Compress old messages into a summary, keep recent ones intact."""
        if len(messages) <= keep_recent:
            return messages

        old = messages[:-keep_recent]
        recent = messages[-keep_recent:]

        # Create a summary of old messages
        summary_parts = []
        for msg in old[-20:]:  # Summarize last 20 old messages
            role = msg.get("role", "user")
            content = str(msg.get("content", ""))[:200]
            summary_parts.append(f"[{role}]: {content}")

        summary = {
            "role": "system",
            "content": f"[خلاصه مکالمه قبلی ({len(old)} پیام)]:\n" + "\n".join(summary_parts)
        }

        return [summary] + recent

    @property
    def stats(self) -> dict:
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "max_response": self.max_response_tokens,
            "available": self.available_tokens,
        }

_instance = None

def get_context_manager() -> Any:
    """Get or create the global ContextManager."""
    global _instance
    if _instance is None:
        _instance = ContextManager()
    return _instance


