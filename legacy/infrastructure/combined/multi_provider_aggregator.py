
from __future__ import annotations
"""
MultiProviderAggregator — Fan-out to providers + aggregate responses.
"""
import asyncio, logging
from typing import Any, Callable, Dict



logger = logging.getLogger(__name__)

class MultiProviderAggregator:
    """Send to multiple providers, aggregate and select best response."""

    def __init__(self, strategy: str = "best") -> None:
        self._providers: Dict[str, Callable] = {}
        self._strategy = strategy

    def add(self, name: str, provider: Callable) -> Any:
        self._providers[name] = provider

    async def query(self, request: Any) -> Dict:
        tasks = {name: asyncio.create_task(fn(request)) for name, fn in self._providers.items()}
        results = {}
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception as e:
                results[name] = {"error": str(e)}

        successful = {k: v for k, v in results.items() if not isinstance(v, dict) or "error" not in v}
        if self._strategy == "best" and successful:
            return {"best": max(successful.items(), key=lambda x: len(str(x[1])))[1], "all": results}
        return {"all": results}


