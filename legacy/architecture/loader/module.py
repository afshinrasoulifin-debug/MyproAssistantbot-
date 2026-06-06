
from __future__ import annotations
"""
architecture.loader.module — ModuleLoader, RuntimeLoader, AssetLoader
════════════════════════════════════════════════════════════════════
Dynamic module loading with dependency resolution.
Covers: module-loader, runtime-loader, asset-loader, module, loader
"""
import importlib, logging, time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class ModuleLoader:
    """Dynamic Python module loader with caching."""
    def __init__(self) -> None:
        self._loaded: Dict[str, Any] = {}
        self._load_order: List[str] = []
        self._load_times: Dict[str, float] = {}

    def load(self, module_path: str, alias: Optional[str] = None) -> Any:
        key = alias or module_path
        if key in self._loaded:
            return self._loaded[key]
        t0 = time.time()
        try:
            mod = importlib.import_module(module_path)
            self._loaded[key] = mod
            self._load_order.append(key)
            self._load_times[key] = time.time() - t0
            logger.debug("Loaded module: %s (%.3fs)", key, self._load_times[key])
            return mod
        except Exception as exc:
            logger.error("Failed to load %s: %s", module_path, exc)
            return None

    def reload(self, key: str) -> Any:
        mod = self._loaded.get(key)
        if mod:
            try:
                importlib.reload(mod)
                return mod
            except Exception as exc:
                logger.error("Failed to reload %s: %s", key, exc)
        return None

    def is_loaded(self, key: str) -> bool:
        return key in self._loaded

    def get(self, key: str) -> Optional[Any]:
        return self._loaded.get(key)

    @property
    def stats(self) -> Dict[str, Any]:
        return {"loaded": len(self._loaded), "order": self._load_order,
                "total_time": round(sum(self._load_times.values()), 3)}

class RuntimeLoader(ModuleLoader):
    """Loader with runtime dependency resolution."""
    def __init__(self) -> None:
        super().__init__()
        self._deps: Dict[str, List[str]] = {}

    def register_deps(self, module: str, deps: List[str]) -> None:
        self._deps[module] = deps

    def load_with_deps(self, module_path: str) -> Any:
        for dep in self._deps.get(module_path, []):
            if not self.is_loaded(dep):
                self.load(dep)
        return self.load(module_path)

class AssetLoader:
    """Load non-code assets (configs, templates, data files)."""
    def __init__(self, base_path: str = ".") -> None:
        self.base_path = base_path
        self._cache: Dict[str, Any] = {}

    def load_json(self, path: str) -> Any:
        if path in self._cache:
            return self._cache[path]
        import json, os
        full = os.path.join(self.base_path, path)
        try:
            with open(full) as f:
                data = json.load(f)
            self._cache[path] = data
            return data
        except Exception as exc:
            logger.error("Asset load error %s: %s", path, exc)
            return None

    def load_text(self, path: str) -> Optional[str]:
        import os
        full = os.path.join(self.base_path, path)
        try:
            with open(full) as f:
                return f.read()
        except Exception:
            return None


