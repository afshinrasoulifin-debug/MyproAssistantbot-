
from __future__ import annotations
"""ModelRuntime — Model lifecycle management."""
import logging
from typing import Dict, Any



logger = logging.getLogger(__name__)

class ModelRuntime:
    """Manage model loading, unloading, versioning."""

    def __init__(self) -> None:
        self._loaded: Dict[str, Any] = {}
        self._versions: Dict[str, str] = {}

    def load(self, name: str, version: str = "latest", config: dict = None) -> Any:
        self._loaded[name] = config or {}
        self._versions[name] = version
        logger.info("ModelRuntime: loaded %s@%s", name, version)

    def unload(self, name: str) -> Any:
        self._loaded.pop(name, None)
        self._versions.pop(name, None)

    def is_loaded(self, name: str) -> bool:
        return name in self._loaded

    def list_models(self) -> Dict[str, str]:
        return dict(self._versions)


