
from __future__ import annotations
"""ProviderWrapper — Wrap any provider with extra capabilities."""

import asyncio
import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)



class ProviderWrapper:
    """ProviderWrapper — Wrap any provider with extra capabilities."""

    def __init__(self, wrapped: Any = None, *, name: str = "provider_wrapper") -> None:
        self._wrapped = wrapped
        self.name = name
        self._before_hooks: List = []
        self._after_hooks: List = []
        self._stats = {"calls": 0, "errors": 0, "total_ms": 0.0}
        logger.info("ProviderWrapper '%s' initialized", name)

    def before(self, hook: Any) -> "ProviderWrapper":
        """Add a before hook."""
        self._before_hooks.append(hook)
        return self

    def after(self, hook: Any) -> "ProviderWrapper":
        """Add an after hook."""
        self._after_hooks.append(hook)
        return self

    async def call(self, method: str, *args, **kwargs) -> Dict:
        """Call a method on the wrapped object with hooks."""
        t0 = time.monotonic()
        self._stats["calls"] += 1

        # Before hooks
        for hook in self._before_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(method, args, kwargs)
                else:
                    hook(method, args, kwargs)
            except Exception as e:
                logger.warning("ProviderWrapper before hook error: %s", e)

        # Execute
        try:
            if self._wrapped:
                fn = getattr(self._wrapped, method, None)
                if fn and callable(fn):
                    if asyncio.iscoroutinefunction(fn):
                        result = await fn(*args, **kwargs)
                    else:
                        result = fn(*args, **kwargs)
                else:
                    result = None
            else:
                result = None

            elapsed = (time.monotonic() - t0) * 1000
            self._stats["total_ms"] += elapsed
        except Exception as e:
            self._stats["errors"] += 1
            return {"ok": False, "error": str(e)}

        # After hooks
        for hook in self._after_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    result = await hook(result) or result
                else:
                    result = hook(result) or result
            except Exception as e:
                logger.warning("ProviderWrapper after hook error: %s", e)

        return {"ok": True, "result": result, "ms": round(elapsed, 2)}

    @property
    def wrapped(self) -> Any:
        return self._wrapped

    def get_stats(self) -> dict:
        avg = (self._stats["total_ms"] / self._stats["calls"]) if self._stats["calls"] else 0
        return {**self._stats, "avg_ms": round(avg, 2)}


