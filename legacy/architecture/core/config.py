
from __future__ import annotations
"""
architecture.core.config — ConfigManager, FeatureFlags, RemoteConfig, AdvancedConfig
════════════════════════════════════════════════════════════════════════════════════
Centralized configuration with feature flags, hot-reloadable settings,
and environment-aware defaults.

Covers: config-manager, remote-config, advanced-config, feature-flags, hidden-flags
"""


import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set



logger = logging.getLogger(__name__)


@dataclass
class FeatureFlag:
    name: str
    enabled: bool = False
    description: str = ""
    rollout_pct: float = 100.0
    allowed_users: Set[int] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)

    def is_enabled_for(self, user_id: int = 0) -> bool:
        if not self.enabled:
            return False
        if self.allowed_users and user_id not in self.allowed_users:
            return False
        if self.rollout_pct < 100.0:
            return (hash(user_id) % 100) < self.rollout_pct
        return True


class FeatureFlags:
    """Runtime feature flag manager with user-level targeting."""

    def __init__(self) -> None:
        self._flags: Dict[str, FeatureFlag] = {}

    def register(
        self, name: str, enabled: bool = False,
        description: str = "", rollout_pct: float = 100.0,
        allowed_users: Optional[Set[int]] = None,
    ) -> FeatureFlag:
        flag = FeatureFlag(
            name=name, enabled=enabled, description=description,
            rollout_pct=rollout_pct,
            allowed_users=allowed_users or set(),
        )
        self._flags[name] = flag
        return flag

    def is_enabled(self, name: str, user_id: int = 0) -> bool:
        flag = self._flags.get(name)
        if flag is None:
            return False
        return flag.is_enabled_for(user_id)

    def toggle(self, name: str, enabled: bool) -> bool:
        flag = self._flags.get(name)
        if flag:
            flag.enabled = enabled
            return True
        return False

    def all_flags(self) -> Dict[str, bool]:
        return {n: f.enabled for n, f in self._flags.items()}

    def export(self) -> List[Dict[str, Any]]:
        return [
            {"name": f.name, "enabled": f.enabled, "rollout_pct": f.rollout_pct,
             "description": f.description}
            for f in self._flags.values()
        ]


class RemoteConfig:
    """
    Remote/file-based configuration that can be hot-reloaded.
    Falls back to environment variables → defaults.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._path = Path(config_path) if config_path else None
        self._data: Dict[str, Any] = {}
        self._last_load: float = 0
        self._watchers: List[Callable[[str, Any, Any], None]] = []
        self._load()

    def _load(self) -> None:
        if self._path and self._path.exists():
            try:
                with open(self._path) as f:
                    self._data = json.load(f)
                self._last_load = time.time()
                logger.debug("RemoteConfig loaded from %s", self._path)
            except Exception as exc:
                logger.warning("RemoteConfig load error: %s", exc)

    def reload(self) -> bool:
        old = dict(self._data)
        self._load()
        # Notify watchers of changes
        for key in set(old.keys()) | set(self._data.keys()):
            old_val = old.get(key)
            new_val = self._data.get(key)
            if old_val != new_val:
                for watcher in self._watchers:
                    try:
                        watcher(key, old_val, new_val)
                    except Exception as e:
                        logger.debug("Suppressed: %s", e)
        return self._data != old

    def get(self, key: str, default: Any = None) -> Any:
        # Priority: loaded config → env var → default
        if key in self._data:
            return self._data[key]
        env_key = key.upper().replace(".", "_").replace("-", "_")
        env_val = os.environ.get(env_key)
        if env_val is not None:
            return env_val
        return default

    def set(self, key: str, value: Any) -> None:
        old = self._data.get(key)
        self._data[key] = value
        for watcher in self._watchers:
            try:
                watcher(key, old, value)
            except Exception as e:
                logger.debug("Suppressed: %s", e)

    def watch(self, callback: Callable[[str, Any, Any], None]) -> None:
        self._watchers.append(callback)

    def save(self) -> bool:
        if self._path:
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with open(self._path, "w") as f:
                    json.dump(self._data, f, indent=2, ensure_ascii=False)
                return True
            except Exception as exc:
                logger.error("RemoteConfig save error: %s", exc)
        return False


class AdvancedConfig:
    """
    Combines FeatureFlags + RemoteConfig into unified config layer.
    Provides type-safe accessors and validation.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        self.flags = FeatureFlags()
        self.remote = RemoteConfig(config_path)
        self._defaults: Dict[str, Any] = {}
        self._validators: Dict[str, Callable[[Any], bool]] = {}

    def define(
        self, key: str, default: Any = None,
        validator: Optional[Callable[[Any], bool]] = None,
    ) -> None:
        self._defaults[key] = default
        if validator:
            self._validators[key] = validator

    def get(self, key: str, default: Any = None) -> Any:
        val = self.remote.get(key, self._defaults.get(key, default))
        validator = self._validators.get(key)
        if validator and val is not None and not validator(val):
            logger.warning("Config validation failed for %s=%s, using default", key, val)
            return self._defaults.get(key, default)
        return val

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(self.get(key, default))
        except (TypeError, ValueError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        try:
            return float(self.get(key, default))
        except (TypeError, ValueError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        val = self.get(key, default)
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1", "yes")

    def get_list(self, key: str, default: Optional[List] = None) -> List:
        val = self.get(key, default or [])
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            return [v.strip() for v in val.split(",") if v.strip()]
        return default or []

    def export(self) -> Dict[str, Any]:
        return {
            "config": {k: self.get(k) for k in self._defaults},
            "flags": self.flags.export(),
        }


# ── Singleton ──
_config: Optional[AdvancedConfig] = None

def get_config(config_path: Optional[str] = None) -> AdvancedConfig:
    global _config
    if _config is None:
        _config = AdvancedConfig(config_path)
    return _config


