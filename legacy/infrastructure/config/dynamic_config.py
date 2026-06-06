
from __future__ import annotations
"""DynamicConfig — Hot-reload configuration."""
import json, logging, os
from typing import Any, Dict



logger = logging.getLogger(__name__)

class DynamicConfig:
    def __init__(self, config_path: str = "data/dynamic_config.json") -> None:
        self._path = config_path
        self._config: Dict[str, Any] = {}
        self._load()

    def _load(self) -> Any:
        try:
            if os.path.exists(self._path):
                with open(self._path) as f:
                    self._config = json.load(f)
        except Exception as _exc:
            logger.debug("Suppressed: %s", _exc)

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> Any:
        self._config[key] = value
        self._save()

    def _save(self) -> Any:
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, 'w') as f:
                json.dump(self._config, f, indent=2)
        except Exception as _exc:
            logger.debug("Suppressed: %s", _exc)

    def reload(self) -> Any:
        self._load()


