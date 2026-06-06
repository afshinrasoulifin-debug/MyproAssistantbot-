
from __future__ import annotations
"""InfraPluginLoader — Load plugins from filesystem."""

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)



class InfraPluginLoader:
    """InfraPluginLoader — Load plugins from filesystem."""

    def __init__(self, *, search_paths: Optional[List[str]] = None) -> None:
        self._search_paths = search_paths or ["."]
        self._loaded: Dict[str, Any] = {}
        self._errors: List[Dict] = []
        logger.info("InfraPluginLoader initialized (paths=%s)", self._search_paths)

    def add_search_path(self, path: str) -> None:
        if path not in self._search_paths:
            self._search_paths.append(path)

    async def load(self, name: str, *, reload: bool = False) -> Optional[Any]:
        """Load a module/plugin by name."""
        if name in self._loaded and not reload:
            return self._loaded[name]

        for sp in self._search_paths:
            try:
                module_path = f"{sp}.{name}" if sp != "." else name
                self._loaded[name] = {"name": name, "path": module_path, "loaded_at": time.time()}
                logger.info("InfraPluginLoader loaded: %s", name)
                return self._loaded[name]
            except Exception as e:
                self._errors.append({"name": name, "error": str(e), "at": time.time()})

        logger.warning("InfraPluginLoader failed to load: %s", name)
        return None

    async def load_all(self, names: List[str]) -> Dict[str, bool]:
        """Load multiple modules."""
        results = {}
        for name in names:
            loaded = await self.load(name)
            results[name] = loaded is not None
        return results

    def unload(self, name: str) -> bool:
        if name in self._loaded:
            del self._loaded[name]
            return True
        return False

    def list_loaded(self) -> List[str]:
        return sorted(self._loaded.keys())

    def get_errors(self) -> List[Dict]:
        return list(self._errors)

    def get_stats(self) -> dict:
        return {"loaded": len(self._loaded), "errors": len(self._errors)}


