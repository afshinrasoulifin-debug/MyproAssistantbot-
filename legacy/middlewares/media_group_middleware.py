
from __future__ import annotations
"""
tg_bot/middlewares/media_group_middleware.py — Media Group Handler v9.4
Collects photos sent as a group and processes them together.
"""
import asyncio
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject



logger = logging.getLogger(__name__)


class MediaGroupMiddleware(BaseMiddleware):
    """Collect media group items and process as batch."""

    def __init__(self, latency: float = 1.0):
        self._groups: Dict[str, List[Message]] = defaultdict(list)
        self._latency = latency
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.media_group_id:
            return await handler(event, data)

        group_id = event.media_group_id
        self._groups[group_id].append(event)

        async with self._locks[group_id]:
            if len(self._groups[group_id]) == 1:
                # First message in group — wait for others
                await asyncio.sleep(self._latency)

        # Only process on the first message (which waited)
        if self._groups[group_id][0].message_id == event.message_id:
            data["media_group"] = self._groups.pop(group_id, [])
            self._locks.pop(group_id, None)  # Cleanup lock for this group
            return await handler(event, data)

        return None  # Skip individual items


