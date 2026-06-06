
from __future__ import annotations
"""architecture.layer.runtime_layer — RuntimeLayerImpl, PlatformLayerImpl
═════════════════════════════════════════════════════════════════════
Runtime and platform layer implementations."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)



class RuntimeLayerImpl:
    """architecture.layer.runtime_layer — RuntimeLayerImpl, PlatformLayerImpl
═════════════════════════════════════════════════════════════════════
Runtime and platform layer implementations."""

    def __init__(self, *, name: str = "runtime_layer"):
        self.name = name
        self._registry: Dict[str, Any] = {}
        self._stats = {"ops": 0, "errors": 0}
        logger.info("RuntimeLayerImpl '%s' initialized", name)

    def register(self, key: str, value: Any) -> None:
        self._registry[key] = value

    def resolve(self, key: str) -> Optional[Any]:
        return self._registry.get(key)

    async def execute(self, op: str, data: Any = None) -> Dict:
        self._stats["ops"] += 1
        try:
            handler = self._registry.get(op)
            if handler and callable(handler):
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(data)
                else:
                    result = handler(data)
                return {"ok": True, "result": result}
            return {"ok": True, "operation": op}
        except Exception as e:
            self._stats["errors"] += 1
            return {"ok": False, "error": str(e)}

    def list_registered(self) -> List[str]:
        return sorted(self._registry.keys())

    def get_stats(self) -> dict:
        return {**self._stats, "registered": len(self._registry)}


