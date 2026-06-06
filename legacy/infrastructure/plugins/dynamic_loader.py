
from __future__ import annotations
"""InfraDynamicLoader — Dynamic component loader."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)



class InfraDynamicLoader:
    """InfraDynamicLoader — Dynamic component loader."""

    def __init__(self) -> None:
        self._plugins: Dict[str, Dict] = {}
        self._hooks: Dict[str, List] = {}
        self._stats = {"loaded": 0, "errors": 0}
        logger.info("InfraDynamicLoader initialized")

    def register(self, name: str, plugin: Any, *, version: str = "1.0") -> None:
        """Register a plugin."""
        self._plugins[name] = {
            "instance": plugin,
            "version": version,
            "enabled": True,
            "loaded_at": time.time(),
        }
        self._stats["loaded"] += 1
        logger.info("Plugin registered: %s v%s", name, version)

    def enable(self, name: str) -> bool:
        if name in self._plugins:
            self._plugins[name]["enabled"] = True
            return True
        return False

    def disable(self, name: str) -> bool:
        if name in self._plugins:
            self._plugins[name]["enabled"] = False
            return True
        return False

    def get_plugin(self, name: str) -> Optional[Any]:
        p = self._plugins.get(name)
        if p and p["enabled"]:
            return p["instance"]
        return None

    async def invoke_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Invoke all registered hooks."""
        results = []
        for handler in self._hooks.get(hook_name, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(*args, **kwargs)
                else:
                    result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                self._stats["errors"] += 1
                logger.warning("Hook '%s' error: %s", hook_name, e)
        return results

    def on(self, hook_name: str, handler: Any) -> None:
        self._hooks.setdefault(hook_name, []).append(handler)

    def list_plugins(self) -> List[Dict]:
        return [{
            "name": n,
            "version": p["version"],
            "enabled": p["enabled"],
        } for n, p in self._plugins.items()]

    def get_stats(self) -> dict:
        enabled = sum(1 for p in self._plugins.values() if p["enabled"])
        return {**self._stats, "total": len(self._plugins), "enabled": enabled}


