
from __future__ import annotations
"""InfraFeatureFlags — Infrastructure-level feature flags."""

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)



class InfraFeatureFlags:
    """InfraFeatureFlags — Infrastructure-level feature flags."""

    def __init__(self, defaults: Optional[Dict] = None) -> None:
        self._store: Dict[str, Any] = dict(defaults or {})
        self._listeners: Dict[str, List] = {}
        self._history: List[Dict] = []
        logger.info("InfraFeatureFlags initialized (%d defaults)", len(self._store))

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value."""
        return self._store.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a config value and notify listeners."""
        old = self._store.get(key)
        self._store[key] = value
        self._history.append({"key": key, "old": old, "new": value, "at": time.time()})
        for listener in self._listeners.get(key, []):
            try:
                listener(key, value, old)
            except Exception as e:
                logger.warning("InfraFeatureFlags listener error: %s", e)

    def on_change(self, key: str, listener: Any) -> None:
        """Register a change listener for a config key."""
        self._listeners.setdefault(key, []).append(listener)

    def get_all(self) -> Dict[str, Any]:
        """Return all config as a dict."""
        return dict(self._store)

    def is_enabled(self, flag: str) -> bool:
        """Check if a feature flag is enabled."""
        val = self._store.get(flag, False)
        return bool(val)

    def bulk_set(self, values: Dict[str, Any]) -> int:
        """Set multiple config values at once."""
        for k, v in values.items():
            self.set(k, v)
        return len(values)

    def get_history(self, limit: int = 20) -> List[Dict]:
        return self._history[-limit:]


