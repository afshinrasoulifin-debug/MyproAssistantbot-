
from __future__ import annotations
"""
architecture.service.sync — SyncService, LiveSync, RealtimeSync, StateSync, DataSync, SmartSync, FastSync
═════════════════════════════════════════════════════════════════════════════════════════════════════════
Synchronization services for state, data, and real-time updates.
Covers: sync, sync-service, live-sync, realtime-sync, state-sync, data-sync, smart-sync, fast-sync, remote-sync, cloud-sync
"""
import logging, time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

class SyncService:
    """Base synchronization service with change detection."""
    def __init__(self) -> None:
        self._state: Dict[str, Any] = {}
        self._versions: Dict[str, int] = defaultdict(int)
        self._listeners: List[Callable] = []

    def set(self, key: str, value: Any) -> bool:
        old = self._state.get(key)
        if old != value:
            self._state[key] = value
            self._versions[key] += 1
            for listener in self._listeners:
                try: listener(key, old, value)
                except Exception as _exc:
                    logger.debug("Suppressed: %s", _exc)
            pass
            return True
        return False

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def get_version(self, key: str) -> int:
        return self._versions.get(key, 0)

    def on_change(self, callback: Callable) -> None:
        self._listeners.append(callback)

    def diff(self, other_versions: Dict[str, int]) -> Dict[str, Any]:
        changes = {}
        for key, ver in self._versions.items():
            if other_versions.get(key, 0) < ver:
                changes[key] = self._state[key]
        return changes

class LiveSync(SyncService):
    """Real-time sync with debouncing and batching."""
    def __init__(self, debounce_s: float = 0.5) -> None:
        super().__init__()
        self._debounce = debounce_s
        self._pending: Dict[str, Any] = {}
        self._last_flush: float = 0

    def set(self, key: str, value: Any) -> bool:
        changed = super().set(key, value)
        if changed:
            self._pending[key] = value
        return changed

    async def flush(self) -> Dict[str, Any]:
        if not self._pending:
            return {}
        batch = dict(self._pending)
        self._pending.clear()
        self._last_flush = time.time()
        return batch

class RealtimeSync(LiveSync):
    """Extends LiveSync with WebSocket-style push notifications."""
    def __init__(self) -> None:
        super().__init__(debounce_s=0.1)
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, key: str, callback: Callable) -> None:
        self._subscribers[key].append(callback)

    def set(self, key: str, value: Any) -> bool:
        changed = super().set(key, value)
        if changed:
            for cb in self._subscribers.get(key, []):
                try: cb(key, value)
                except Exception as _exc:
                    logger.debug("Suppressed: %s", _exc)
            pass
        return changed

class StateSync(SyncService):
    """Persistent state sync with snapshots."""
    def __init__(self, persist_path: Optional[str] = None) -> None:
        super().__init__()
        self._path = persist_path

    def snapshot(self) -> Dict[str, Any]:
        return {"state": dict(self._state), "versions": dict(self._versions), "time": time.time()}

    def restore(self, snapshot: Dict[str, Any]) -> None:
        self._state = snapshot.get("state", {})
        self._versions = defaultdict(int, snapshot.get("versions", {}))

    def save(self) -> bool:
        if self._path:
            try:
                import json
                with open(self._path, "w") as f:
                    json.dump(self.snapshot(), f, ensure_ascii=False)
                return True
            except Exception as _exc:
                logger.debug("Suppressed: %s", _exc)
            pass
        return False

    def load(self) -> bool:
        if self._path:
            try:
                import json
                with open(self._path) as f:
                    self.restore(json.load(f))
                return True
            except Exception as _exc:
                logger.debug("Suppressed: %s", _exc)
            pass
        return False

class DataSync(SyncService):
    """Data synchronization with conflict resolution."""
    def __init__(self) -> None:
        super().__init__()
        self._timestamps: Dict[str, float] = {}

    def set(self, key: str, value: Any) -> bool:
        self._timestamps[key] = time.time()
        return super().set(key, value)

    def merge(self, remote_state: Dict[str, Any], remote_timestamps: Dict[str, float]) -> Dict[str, str]:
        resolution = {}
        for key, remote_val in remote_state.items():
            local_ts = self._timestamps.get(key, 0)
            remote_ts = remote_timestamps.get(key, 0)
            if remote_ts > local_ts:
                super().set(key, remote_val)
                self._timestamps[key] = remote_ts
                resolution[key] = "remote_wins"
            else:
                resolution[key] = "local_wins"
        return resolution

SmartSync = LiveSync
FastSync = RealtimeSync


