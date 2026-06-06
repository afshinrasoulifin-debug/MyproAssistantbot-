
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/outbound_queue.py — Outbound Message Queue v9.4
Queue outbound Telegram messages with retry on failure.
Prevents message loss when Telegram API fails.
"""
import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Optional

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


@dataclass
class OutboundMessage:
    chat_id: int
    text: str
    parse_mode: str = "Markdown"
    reply_to: int = 0
    retries: int = 0
    max_retries: int = 3
    created_at: float = 0.0

    def __post_init__(self) -> Any:
        if not self.created_at:
            self.created_at = time.time()


class OutboundQueue:
    """Queue and retry outbound Telegram messages."""

    def __init__(self, max_queue_size: int = 10000, rate_limit: float = 0.05) -> None:
        self._queue: deque = deque(maxlen=max_queue_size)
        self._dead_letter: deque = deque(maxlen=1000)
        self._rate_limit = rate_limit  # seconds between messages
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._sent_count = 0
        self._failed_count = 0

    async def enqueue(self, msg: OutboundMessage) -> Any:
        """Add message to outbound queue."""
        self._queue.append(msg)

    async def start(self, bot: Any) -> Any:
        """Start processing outbound queue."""
        self._running = True
        self._task = asyncio.create_task(self._worker(bot))
        logger.info("Outbound queue started")

    async def stop(self) -> Any:
        """Stop processing."""
        self._running = False
        if self._task:
            self._task.cancel()

    async def _worker(self, bot: Any) -> Any:
        """Process outbound messages with rate limiting."""
        while self._running:
            if not self._queue:
                await asyncio.sleep(0.1)
                continue

            msg = self._queue.popleft()
            try:
                kwargs = {"chat_id": msg.chat_id, "text": msg.text}
                if msg.parse_mode:
                    kwargs["parse_mode"] = msg.parse_mode
                if msg.reply_to:
                    kwargs["reply_to_message_id"] = msg.reply_to
                await bot.send_message(**kwargs)
                self._sent_count += 1
                await asyncio.sleep(self._rate_limit)
            except ArkiBaseError as e:
                msg.retries += 1
                if msg.retries < msg.max_retries:
                    self._queue.appendleft(msg)  # Re-queue
                    await asyncio.sleep(2 ** msg.retries)  # Exponential backoff
                else:
                    self._dead_letter.append(msg)
                    self._failed_count += 1
                    logger.error("Message to %d failed after %d retries: %s",
                               msg.chat_id, msg.max_retries, e)

    @property
    def stats(self) -> dict:
        return {
            "queue_size": len(self._queue),
            "dead_letter_size": len(self._dead_letter),
            "sent": self._sent_count,
            "failed": self._failed_count,
            "running": self._running,
        }


_queue: Optional[OutboundQueue] = None

def get_outbound_queue() -> OutboundQueue:
    global _queue
    if _queue is None:
        _queue = OutboundQueue()
    return _queue

async def send_long_text(bot: Any, chat_id: int, text: str, parse_mode: str = "Markdown", **kwargs) -> None:
    """Send long text by splitting into chunks."""
    from arki_project.utils.models_registry import split_for_telegram
    chunks = split_for_telegram(text)
    for chunk in chunks:
        try:
            await bot.send_message(chat_id, chunk, parse_mode=parse_mode, **kwargs)
        except ArkiBaseError:
            await bot.send_message(chat_id, chunk, **kwargs)


