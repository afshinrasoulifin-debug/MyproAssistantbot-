
from __future__ import annotations
"""MultiClient — Fan-out client for multi-model comparison."""
import asyncio, logging
from typing import Any, Dict, List



logger = logging.getLogger(__name__)

class MultiClient:
    """Send same request to multiple models simultaneously."""

    def __init__(self) -> None:
        self._clients: Dict[str, Any] = {}

    def add(self, name: str, client: Any) -> Any:
        self._clients[name] = client

    async def race(self, messages: list, models: List[str] = None, **kwargs) -> Dict[str, Any]:
        targets = models or list(self._clients.keys())
        tasks = {}
        for name in targets:
            if name in self._clients:
                tasks[name] = asyncio.create_task(
                    self._clients[name].complete(messages, **kwargs)
                )
        results = {}
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception as e:
                results[name] = {"error": str(e)}
        return results


