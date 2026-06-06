
from __future__ import annotations
"""
architecture.bridge.data — DataBridge (RemoteSync, CloudSync, FastSync integration)
════════════════════════════════════════════════════════════════════════════════════
Data bridge for synchronizing across storage layers.
Covers: data-bridge, remote-sync, cloud-sync, fast-sync
"""
import logging, time
from typing import Any, Dict



logger = logging.getLogger(__name__)

class DataBridge:
    """Bridge for data synchronization between local and remote stores."""
    def __init__(self) -> None:
        self._local: Dict[str, Any] = {}
        self._remote: Dict[str, Any] = {}
        self._sync_log: list = []

    def set_local(self, key: str, value: Any) -> None:
        self._local[key] = value

    def set_remote(self, key: str, value: Any) -> None:
        self._remote[key] = value

    def sync_to_remote(self) -> Dict[str, str]:
        results = {}
        for key, val in self._local.items():
            if self._remote.get(key) != val:
                self._remote[key] = val
                results[key] = "synced"
        self._sync_log.append({"direction": "push", "time": time.time(), "keys": list(results.keys())})
        return results

    def sync_from_remote(self) -> Dict[str, str]:
        results = {}
        for key, val in self._remote.items():
            if self._local.get(key) != val:
                self._local[key] = val
                results[key] = "synced"
        self._sync_log.append({"direction": "pull", "time": time.time(), "keys": list(results.keys())})
        return results

    def full_sync(self) -> Dict[str, Any]:
        pushed = self.sync_to_remote()
        pulled = self.sync_from_remote()
        return {"pushed": pushed, "pulled": pulled}


