
from __future__ import annotations
"""
architecture.loader.bootstrap_loader — BootstrapLoader, PackageLoader, UpdateLoader
═══════════════════════════════════════════════════════════════════════════════════
Loaders for bootstrap, packages, and updates.
Covers: bootstrap-loader, package-loader, update-loader
"""
import logging, time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

class BootstrapLoader:
    """Load and initialize components during bootstrap phase."""
    def __init__(self) -> None:
        self._loaders: List[tuple] = []
        self._loaded: Dict[str, Any] = {}

    def register(self, name: str, loader_fn: Callable, priority: int = 50) -> None:
        self._loaders.append((priority, name, loader_fn))
        self._loaders.sort(key=lambda x: x[0])

    async def load_all(self) -> Dict[str, Any]:
        import asyncio
        results = {}
        for priority, name, fn in self._loaders:
            t0 = time.time()
            try:
                result = fn()
                if asyncio.iscoroutine(result):
                    result = await result
                self._loaded[name] = result
                results[name] = {"status": "ok", "time": round(time.time()-t0, 3)}
            except Exception as exc:
                results[name] = {"status": "error", "error": str(exc)}
        return results

class PackageLoader:
    """Load package dependencies."""
    def __init__(self) -> None:
        self._packages: Dict[str, dict] = {}

    def register(self, name: str, version: str, loader_fn: Optional[Callable] = None) -> None:
        self._packages[name] = {"version": version, "loader": loader_fn, "loaded": False}

    def load(self, name: str) -> bool:
        pkg = self._packages.get(name)
        if pkg and pkg.get("loader"):
            try:
                pkg["loader"]()
                pkg["loaded"] = True
                return True
            except Exception:
                return False
        return False

class UpdateLoader:
    """Load and apply updates."""
    def __init__(self) -> None:
        self._updates: List[dict] = []

    def register(self, version: str, apply_fn: Callable) -> None:
        self._updates.append({"version": version, "fn": apply_fn, "applied": False})

    def apply_pending(self) -> List[str]:
        applied = []
        for update in self._updates:
            if not update["applied"]:
                try:
                    update["fn"]()
                    update["applied"] = True
                    applied.append(update["version"])
                except Exception as exc:
                    logger.error("Update %s failed: %s", update["version"], exc)
        return applied


