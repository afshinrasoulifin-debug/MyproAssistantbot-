
from __future__ import annotations
"""
tg_bot/utils/ai_streaming.py — Streaming AI Responses v9.3
Enables token-by-token streaming for long AI responses.
"""
import logging
import time
from typing import AsyncGenerator, Callable

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class StreamingResponse:
    """
    Manages streaming AI response with live Telegram message updates.
    Updates message every N tokens or T seconds.
    """

    def __init__(self, update_interval: float = 1.5, min_chars: int = 50) -> None:
        self._update_interval = update_interval
        self._min_chars = min_chars
        self._buffer = ""
        self._last_update = 0.0
        self._total_tokens = 0
        self._start_time = 0.0

    async def stream_to_message(
        self,
        token_generator: AsyncGenerator[str, None],
        message: str,
        edit_func: Callable,
        prefix: str = "",
        suffix: str = "",
    ) -> str:
        """
        Stream tokens to a Telegram message with periodic edits.

        Args:
            token_generator: async generator yielding tokens
            message: Telegram message to edit
            edit_func: async function to edit message text
            prefix: text to prepend
            suffix: text to append
        """
        self._start_time = time.monotonic()
        self._last_update = self._start_time
        full_text = ""

        async for token in token_generator:
            full_text += token
            self._total_tokens += 1
            self._buffer += token

            now = time.monotonic()
            if (now - self._last_update >= self._update_interval
                    and len(self._buffer) >= self._min_chars):
                try:
                    display = f"{prefix}{full_text}{suffix}"
                    await edit_func(message, display[:4096])
                    self._last_update = now
                    self._buffer = ""
                except Exception as e:
                    logger.debug("Stream edit failed: %s", e)

        # Final update with complete text
        if self._buffer:
            try:
                display = f"{prefix}{full_text}{suffix}"
                await edit_func(message, display[:4096])
            except Exception as _exc:
                logger.debug("Suppressed: %s", _exc)

        return full_text

    @property
    def stats(self) -> dict:
        elapsed = time.monotonic() - self._start_time if self._start_time else 0
        return {
            "tokens": self._total_tokens,
            "elapsed_s": round(elapsed, 2),
            "tokens_per_s": round(self._total_tokens / max(0.1, elapsed), 1),
        }


