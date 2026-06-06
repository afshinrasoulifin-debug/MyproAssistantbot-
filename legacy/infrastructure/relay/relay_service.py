
from __future__ import annotations
"""RelayService — Background relay service."""

import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)



class RelayService:
    """RelayService — Background relay service."""

    def __init__(self, *, buffer_size: int = 1000) -> None:
        self._channels: Dict[str, List] = {}
        self._buffer_size = buffer_size
        self._stats = {"relayed": 0, "dropped": 0}
        logger.info("RelayService initialized (buffer=%d)", buffer_size)

    def open_channel(self, name: str) -> None:
        """Open a relay channel."""
        if name not in self._channels:
            self._channels[name] = []

    def close_channel(self, name: str) -> bool:
        if name in self._channels:
            del self._channels[name]
            return True
        return False

    async def relay(self, channel: str, data: Any) -> Dict:
        """Relay data through a channel."""
        if channel not in self._channels:
            return {"ok": False, "error": f"Channel not open: {channel}"}

        buf = self._channels[channel]
        if len(buf) >= self._buffer_size:
            buf.pop(0)
            self._stats["dropped"] += 1

        buf.append({"data": data, "relayed_at": time.time()})
        self._stats["relayed"] += 1
        return {"ok": True, "channel": channel, "buffer_size": len(buf)}

    async def drain(self, channel: str, limit: int = 100) -> List[Any]:
        """Drain data from a channel."""
        if channel not in self._channels:
            return []
        items = self._channels[channel][:limit]
        self._channels[channel] = self._channels[channel][limit:]
        return [i["data"] for i in items]

    def list_channels(self) -> List[str]:
        return sorted(self._channels.keys())

    def get_stats(self) -> dict:
        total_buffered = sum(len(b) for b in self._channels.values())
        return {**self._stats, "channels": len(self._channels), "buffered": total_buffered}


