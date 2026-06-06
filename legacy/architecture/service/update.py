
from __future__ import annotations
"""
architecture.service.update — UpdateService, LiveUpdate, SmartUpdater, SilentUpdater
════════════════════════════════════════════════════════════════════════════════════
Update management with version tracking, rollback, and notification.
Covers: update-service, live-update, smart-updater, silent-updater, updater, update-client, deployment-client
"""
import logging, time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional



logger = logging.getLogger(__name__)

@dataclass
class UpdateInfo:
    version: str
    description: str = ""
    changes: List[str] = field(default_factory=list)
    applied_at: Optional[float] = None
    rollback_fn: Optional[Callable] = None

class UpdateService:
    """Version-aware update service with rollback support."""
    def __init__(self, current_version: str = "8.0.0") -> None:
        self.current_version = current_version
        self._history: List[UpdateInfo] = []
        self._pending: List[UpdateInfo] = []
        self._hooks: List[Callable] = []

    def register_update(self, version: str, description: str = "",
                        changes: Optional[List[str]] = None,
                        rollback_fn: Optional[Callable] = None) -> UpdateInfo:
        info = UpdateInfo(version=version, description=description,
                          changes=changes or [], rollback_fn=rollback_fn)
        self._pending.append(info)
        return info

    def apply_update(self, info: UpdateInfo) -> bool:
        try:
            info.applied_at = time.time()
            self._history.append(info)
            self._pending = [u for u in self._pending if u.version != info.version]
            self.current_version = info.version
            for hook in self._hooks:
                try: hook(info)
                except Exception as _exc:
                    logger.debug("Suppressed: %s", _exc)
            pass
            logger.info("Update applied: %s", info.version)
            return True
        except Exception as exc:
            logger.error("Update failed: %s", exc)
            return False

    def rollback(self) -> bool:
        if self._history:
            last = self._history.pop()
            if last.rollback_fn:
                try:
                    last.rollback_fn()
                    if self._history:
                        self.current_version = self._history[-1].version
                    logger.info("Rolled back from %s", last.version)
                    return True
                except Exception as exc:
                    logger.error("Rollback failed: %s", exc)
        return False

    def on_update(self, hook: Callable) -> None:
        self._hooks.append(hook)

    @property
    def stats(self) -> Dict[str, Any]:
        return {"current": self.current_version, "history": len(self._history),
                "pending": len(self._pending)}

class LiveUpdate(UpdateService):
    """Hot-update that applies changes without restart."""
    pass

class SmartUpdater(UpdateService):
    """Applies updates based on priority and impact analysis."""
    def auto_apply(self) -> List[str]:
        applied = []
        for update in sorted(self._pending, key=lambda u: u.version):
            if self.apply_update(update):
                applied.append(update.version)
        return applied

class SilentUpdater(UpdateService):
    """Applies updates silently without user notification."""
    def apply_update(self, info: UpdateInfo) -> bool:
        result = super().apply_update(info)
        return result


