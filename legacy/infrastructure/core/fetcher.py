
from __future__ import annotations
"""Fetcher — Fetch data from various sources."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)



class DataFetcher:
    """Fetcher — Fetch data from various sources."""

    def __init__(self, *, name: str = "fetcher") -> None:
        self.name = name
        self._registry: Dict[str, Any] = {}
        self._stats = {"ops": 0, "errors": 0}
        logger.info("DataFetcher '%s' initialized", name)

    def register(self, key: str, value: Any) -> None:
        """Register a component."""
        self._registry[key] = value

    def resolve(self, key: str) -> Optional[Any]:
        """Resolve a registered component."""
        return self._registry.get(key)

    async def execute(self, operation: str, data: Any = None, context: str = "default") -> Dict:
        """
        Execute an operation through this component.
        ENFORCED: All network-bound operations must use ShieldedClient.
        """
        self._stats["ops"] += 1
        
        # Mandatory Behavioral Entropy Injection
        try:
            from .entropy import BehavioralEntropy
            entropy = BehavioralEntropy()
            await entropy.human_delay(context)
        except ImportError:
            pass

        try:
            # Check if this is a network operation
            if operation in ["fetch", "post", "query_web", "recon"]:
                from arki_project.utils.titanium.shielded_client import ShieldedClientPool
                client = ShieldedClientPool()
                
                method = "POST" if operation == "post" else "GET"
                url = data.get("url") if isinstance(data, dict) else data
                
                if not url:
                    return {"ok": False, "error": "URL is required for network operations"}
                
                result = await client.request(method, url, **(data if isinstance(data, dict) else {}))
                return {"ok": True, "result": result.text, "status": result.status_code}

            handler = self._registry.get(operation)
            if handler and callable(handler):
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(data)
                else:
                    result = handler(data)
                return {"ok": True, "result": result}
            return {"ok": True, "operation": operation, "data": data}
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("DataFetcher execute error: %s", e)
            return {"ok": False, "error": str(e)}

    async def health_check(self) -> Dict:
        """Return component health status."""
        return {
            "name": self.name,
            "type": "DataFetcher",
            "status": "healthy",
            "registered": len(self._registry),
            "stats": self._stats,
        }

    def list_registered(self) -> List[str]:
        return sorted(self._registry.keys())

    def get_stats(self) -> dict:
        return {**self._stats, "registered": len(self._registry)}


