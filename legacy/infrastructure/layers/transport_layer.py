
from __future__ import annotations
"""InfraTransportLayer — Message transport layer."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)



class InfraTransportLayer:
    """InfraTransportLayer — Message transport layer."""

    def __init__(self) -> None:
        self._components: Dict[str, Any] = {}
        self._hooks: Dict[str, List] = {}
        self._active = True
        self._stats = {"calls": 0, "errors": 0}
        logger.info("InfraTransportLayer initialized")

    def register(self, name: str, component: Any) -> None:
        """Register a component in this layer."""
        self._components[name] = component
        logger.debug("InfraTransportLayer registered: %s", name)

    def on(self, event: str, handler: Any) -> None:
        """Register an event hook."""
        self._hooks.setdefault(event, []).append(handler)

    async def process(self, data: Any, *, context: Optional[Dict] = None) -> Dict:
        """Process data through this layer."""
        if not self._active:
            return {"ok": False, "error": "InfraTransportLayer is inactive"}

        self._stats["calls"] += 1
        ctx = dict(context or {})

        # Fire pre-hooks
        for hook in self._hooks.get("pre_process", []):
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(data, ctx)
                else:
                    hook(data, ctx)
            except Exception as e:
                logger.warning("InfraTransportLayer pre-hook error: %s", e)

        try:
            result = {"ok": True, "layer": "InfraTransportLayer", "data": data, "context": ctx}
        except Exception as e:
            self._stats["errors"] += 1
            result = {"ok": False, "error": str(e)}

        # Fire post-hooks
        for hook in self._hooks.get("post_process", []):
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(result)
                else:
                    hook(result)
            except Exception as e:
                logger.warning("InfraTransportLayer post-hook error: %s", e)

        return result

    @property
    def is_active(self) -> bool:
        return self._active

    def activate(self) -> None:
        self._active = True

    def deactivate(self) -> None:
        self._active = False

    def list_components(self) -> List[str]:
        return sorted(self._components.keys())

    def get_stats(self) -> dict:
        return {**self._stats, "components": len(self._components), "active": self._active}


