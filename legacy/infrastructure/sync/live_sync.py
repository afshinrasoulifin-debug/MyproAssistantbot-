
from __future__ import annotations
"""InfraLiveSync — Real-time sync for live data."""

import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)



class InfraLiveSync:
    """InfraLiveSync — Real-time sync for live data."""

    def __init__(self, *, sync_interval: float = 5.0) -> None:
        self._interval = sync_interval
        self._state: Dict[str, Any] = {}
        self._peers: Dict[str, Dict] = {}
        self._dirty: set = set()
        self._stats = {"syncs": 0, "conflicts": 0, "bytes": 0}
        logger.info("InfraLiveSync initialized (interval=%.1fs)", sync_interval)

    def set(self, key: str, value: Any) -> None:
        """Set a value and mark it for sync."""
        self._state[key] = {"value": value, "version": time.time()}
        self._dirty.add(key)

    def get(self, key: str, default: Any = None) -> Any:
        entry = self._state.get(key)
        return entry["value"] if entry else default

    def add_peer(self, peer_id: str, endpoint: str = "") -> None:
        self._peers[peer_id] = {"endpoint": endpoint, "last_sync": 0}

    async def sync(self) -> Dict:
        """Sync dirty state to all peers."""
        if not self._dirty:
            return {"ok": True, "synced": 0}

        keys = list(self._dirty)
        payload = {k: self._state[k] for k in keys if k in self._state}
        size = len(str(payload))

        synced_to = 0
        for peer_id, peer in self._peers.items():
            try:
                # In production: HTTP/WebSocket push to peer
                peer["last_sync"] = time.time()
                synced_to += 1
            except Exception as e:
                self._stats["conflicts"] += 1
                logger.warning("InfraLiveSync sync to '%s' failed: %s", peer_id, e)

        self._dirty.clear()
        self._stats["syncs"] += 1
        self._stats["bytes"] += size

        return {"ok": True, "synced": len(keys), "peers": synced_to, "bytes": size}

    async def receive_sync(self, data: Dict[str, Dict]) -> int:
        """Receive sync data from a peer."""
        applied = 0
        for key, entry in data.items():
            current = self._state.get(key)
            if not current or entry.get("version", 0) > current.get("version", 0):
                self._state[key] = entry
                applied += 1
            else:
                self._stats["conflicts"] += 1
        return applied

    def list_peers(self) -> List[str]:
        return list(self._peers.keys())

    def get_stats(self) -> dict:
        return {**self._stats, "keys": len(self._state), "dirty": len(self._dirty), "peers": len(self._peers)}


