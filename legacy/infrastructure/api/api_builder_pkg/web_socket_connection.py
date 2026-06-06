
"""
api_builder_pkg/web_socket_connection.py — WebSocketConnection
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class WebSocketConnection:
    """Represents an active WebSocket connection with state tracking."""
    conn_id: str
    user_id: str = "anonymous"
    tier: str = "basic"
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    message_count: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    _closed: bool = False

    @property
    def is_alive(self) -> bool:
        """Connection is alive if heartbeat was within 90 seconds."""
        return not self._closed and (time.time() - self.last_heartbeat) < 90

    def mark_activity(self, bytes_in: int = 0, bytes_out: int = 0):
        self.last_activity = time.time()
        self.message_count += 1
        self.bytes_received += bytes_in
        self.bytes_sent += bytes_out




