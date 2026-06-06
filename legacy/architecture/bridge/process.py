
from __future__ import annotations
"""
architecture.bridge.process — ProcessBridge, IPCBridge
═════════════════════════════════════════════════════
Inter-process communication bridges.
Covers: process-bridge, ipc-bridge
"""
import logging, json
from typing import Any, Dict, Optional



logger = logging.getLogger(__name__)

class ProcessBridge:
    """Bridge for cross-process communication via shared files/queues."""
    def __init__(self, channel_id: str = "default") -> None:
        self.channel_id = channel_id
        self._buffer: list = []
        self._received: list = []

    def send(self, data: Any) -> bool:
        try:
            self._buffer.append(json.dumps(data, ensure_ascii=False, default=str))
            return True
        except Exception as exc:
            logger.error("ProcessBridge send error: %s", exc)
            return False

    def receive(self) -> Optional[Any]:
        if self._buffer:
            raw = self._buffer.pop(0)
            return json.loads(raw)
        return None

    def flush(self) -> list:
        items = list(self._buffer)
        self._buffer.clear()
        return items

class IPCBridge(ProcessBridge):
    """IPC bridge with named channels."""
    def __init__(self, name: str = "arki-ipc") -> None:
        super().__init__(name)
        self._channels: Dict[str, list] = {}

    def send_to(self, channel: str, data: Any) -> bool:
        self._channels.setdefault(channel, []).append(data)
        return True

    def receive_from(self, channel: str) -> Optional[Any]:
        ch = self._channels.get(channel, [])
        if ch:
            return ch.pop(0)
        return None


