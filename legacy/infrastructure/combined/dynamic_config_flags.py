
from __future__ import annotations
"""
DynamicConfigFlags — Combines dynamic config + feature flags.
"""
import logging
from typing import Any, Dict



logger = logging.getLogger(__name__)

class DynamicConfigFlags:
    """Dynamic configuration with feature flag system."""

    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self._flags: Dict[str, bool] = {}
        self._overrides: Dict[str, Dict[str, Any]] = {}

    def set(self, key: str, value: Any) -> Any:
        self._config[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def enable_flag(self, flag: str) -> Any:
        self._flags[flag] = True

    def disable_flag(self, flag: str) -> Any:
        self._flags[flag] = False

    def is_enabled(self, flag: str) -> bool:
        return self._flags.get(flag, True)  # Default: enabled

    def set_user_override(self, user_id: str, key: str, value: Any) -> None:
        if user_id not in self._overrides:
            self._overrides[user_id] = {}
        self._overrides[user_id][key] = value

    def get_effective(self, key: str, user_id: str = None) -> Any:
        if user_id and user_id in self._overrides:
            override = self._overrides[user_id].get(key)
            if override is not None:
                return override
        return self._config.get(key)


