
"""
openrouter_client_pkg/context_manager.py — ContextManager
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ContextManager:
    """Manage context window for LLM requests."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count (rough: ~4 chars per token)."""
        return max(1, len(text) // 4)

    @classmethod
    def truncate_messages(
        cls,
        messages: List[ChatMessage],
        max_tokens: int,
        preserve_system: bool = True,
    ) -> List[ChatMessage]:
        """Truncate messages to fit context window."""
        if not messages:
            return messages

        # Always keep system messages
        system_msgs = [
            m for m in messages if m.role == MessageRole.SYSTEM
        ] if preserve_system else []

        other_msgs = [
            m for m in messages if m.role != MessageRole.SYSTEM
        ]

        system_tokens = sum(
            cls.estimate_tokens(m.content) for m in system_msgs
        )
        available = max_tokens - system_tokens - 500  # margin

        # Keep most recent messages that fit
        kept: List[ChatMessage] = []
        used_tokens = 0
        for msg in reversed(other_msgs):
            msg_tokens = cls.estimate_tokens(msg.content)
            if used_tokens + msg_tokens <= available:
                kept.insert(0, msg)
                used_tokens += msg_tokens
            else:
                break

        return system_msgs + kept

    @classmethod
    def summarize_context(
        cls,
        messages: List[ChatMessage],
        max_summary_tokens: int = 500,
    ) -> ChatMessage:
        """Create a summary message from conversation history."""
        # Simple extractive summary
        texts = [
            f"{m.role.value}: {m.content[:200]}"
            for m in messages
            if m.role != MessageRole.SYSTEM
        ]

        summary = "Previous conversation summary:\n"
        for text in texts[-10:]:  # Last 10 messages
            summary += f"- {text[:100]}\n"

        return ChatMessage(
            role=MessageRole.SYSTEM,
            content=summary[:max_summary_tokens * 4],
        )


# ═══════════════════════════════════════════════════════════════════
# Prompt Templates
# ═══════════════════════════════════════════════════════════════════



