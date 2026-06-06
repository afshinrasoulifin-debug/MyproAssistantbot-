
from __future__ import annotations
import os
"""
architecture.transport.channel — SecureChannel, TransportCore, HiddenChannel
════════════════════════════════════════════════════════════════════════════
Secure communication channels with encryption and access control.
Covers: secure-channel, hidden-channel, transport-core
"""
import hashlib, hmac, logging, time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set



logger = logging.getLogger(__name__)

@dataclass
class ChannelMessage:
    content: Any
    sender: str
    channel: str
    timestamp: float = field(default_factory=time.time)
    signature: Optional[str] = None

class TransportCore:
    """Core transport layer managing message channels."""
    def __init__(self) -> None:
        self._channels: Dict[str, List[ChannelMessage]] = {}
        self._subscribers: Dict[str, Set[str]] = {}

    def create_channel(self, name: str) -> None:
        self._channels.setdefault(name, [])
        self._subscribers.setdefault(name, set())

    def subscribe(self, channel: str, subscriber_id: str) -> None:
        self._subscribers.setdefault(channel, set()).add(subscriber_id)

    def send(self, channel: str, content: Any, sender: str = "") -> ChannelMessage:
        msg = ChannelMessage(content=content, sender=sender, channel=channel)
        self._channels.setdefault(channel, []).append(msg)
        return msg

    def receive(self, channel: str, since: float = 0) -> List[ChannelMessage]:
        return [m for m in self._channels.get(channel, []) if m.timestamp > since]

class SecureChannel(TransportCore):
    """Channel with HMAC message signing."""
    def __init__(self, secret: str = "arki-v8-secret") -> None:
        super().__init__()
        self._secret = secret.encode()

    def send(self, channel: str, content: Any, sender: str = "") -> ChannelMessage:
        msg = super().send(channel, content, sender)
        msg.signature = hmac.new(self._secret, str(content).encode(), hashlib.sha256).hexdigest()[:16]
        return msg

    def verify(self, msg: ChannelMessage) -> bool:
        expected = hmac.new(self._secret, str(msg.content).encode(), hashlib.sha256).hexdigest()[:16]
        return msg.signature == expected

class HiddenChannel(SecureChannel):
    """Internal-only channel not exposed to external interfaces."""
    def __init__(self) -> None:
        secret = os.environ.get("CHANNEL_SECRET")
        if not secret:
            import hashlib
            secret = hashlib.sha256(b"arki-default-channel-key").hexdigest()
        super().__init__(secret=secret)
        self._access_list: Set[str] = set()

    def grant_access(self, entity_id: str) -> None:
        self._access_list.add(entity_id)

    def send(self, channel: str, content: Any, sender: str = "") -> ChannelMessage:
        if sender and sender not in self._access_list:
            raise PermissionError(f"Access denied for {sender}")
        return super().send(channel, content, sender)


