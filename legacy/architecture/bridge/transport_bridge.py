
from __future__ import annotations
"""
architecture.bridge.transport_bridge — TransportBridge, StorageBridge
════════════════════════════════════════════════════════════════════
Bridges for transport and storage layers.
Covers: transport-bridge, storage-bridge
"""
import logging
from typing import Any, Dict



logger = logging.getLogger(__name__)

class TransportBridge:
    """Bridge between different transport protocols."""
    def __init__(self) -> None:
        self._protocol_map: Dict[str, str] = {}
        self._message_count = 0

    def map_protocol(self, source_proto: str, target_proto: str) -> None:
        self._protocol_map[source_proto] = target_proto

    def translate(self, data: Any, source_proto: str) -> Any:
        target = self._protocol_map.get(source_proto)
        self._message_count += 1
        return {"data": data, "protocol": target or source_proto}

class StorageBridge:
    """Bridge between different storage backends."""
    def __init__(self) -> None:
        self._backends: Dict[str, Any] = {}

    def register_backend(self, name: str, backend: Any) -> None:
        self._backends[name] = backend

    def migrate(self, from_backend: str, to_backend: str, key: str) -> bool:
        src = self._backends.get(from_backend)
        dst = self._backends.get(to_backend)
        if src and dst and hasattr(src, "get") and hasattr(dst, "set"):
            data = src.get(key)
            if data is not None:
                dst.set(key, data)
                return True
        return False


