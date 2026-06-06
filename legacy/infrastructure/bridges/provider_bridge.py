
from __future__ import annotations
"""InfraProviderBridge — Bridge between AI providers."""

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)



class InfraProviderBridge:
    """InfraProviderBridge — Bridge between AI providers."""

    def __init__(self) -> None:
        self._connections: Dict[str, Any] = {}
        self._queue: List[Dict] = []
        self._stats = {"bridged": 0, "errors": 0, "bytes": 0}
        logger.info("InfraProviderBridge initialized")

    def connect(self, name: str, target: Any, *, config: Optional[Dict] = None) -> None:
        """Establish a bridge connection."""
        self._connections[name] = {
            "target": target,
            "config": config or {},
            "connected_at": time.time(),
        }
        logger.info("InfraProviderBridge connected: %s", name)

    def disconnect(self, name: str) -> bool:
        """Remove a bridge connection."""
        if name in self._connections:
            del self._connections[name]
            return True
        return False

    async def send(self, target: str, data: Any) -> Dict:
        """Send data across the bridge to a named target."""
        if target not in self._connections:
            self._stats["errors"] += 1
            return {"ok": False, "error": f"Not connected: {target}"}

        conn = self._connections[target]
        try:
            payload = data if isinstance(data, dict) else {"data": data}
            size = len(str(payload))
            self._stats["bridged"] += 1
            self._stats["bytes"] += size
            logger.debug("InfraProviderBridge sent %d bytes to %s", size, target)
            return {"ok": True, "target": target, "size": size}
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("InfraProviderBridge send error: %s", e)
            return {"ok": False, "error": str(e)}

    async def broadcast(self, data: Any) -> Dict[str, Dict]:
        """Send data to all connected targets."""
        results = {}
        for name in self._connections:
            results[name] = await self.send(name, data)
        return results

    @property
    def connected(self) -> List[str]:
        return list(self._connections.keys())

    def get_stats(self) -> dict:
        return {**self._stats, "connections": len(self._connections)}


