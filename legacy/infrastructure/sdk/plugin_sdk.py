
from __future__ import annotations
"""PluginSDK — SDK for building plugins."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)



class PluginSDK:
    """PluginSDK — SDK for building plugins."""

    def __init__(self, *, version: str = "1.0") -> None:
        self.version = version
        self._extensions: Dict[str, Any] = {}
        self._hooks: Dict[str, List] = {}
        self._initialized = False
        logger.info("PluginSDK v%s initialized", version)

    async def initialize(self) -> None:
        """Initialize the SDK."""
        self._initialized = True
        for hook in self._hooks.get("init", []):
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(self)
                else:
                    hook(self)
            except Exception as e:
                logger.warning("PluginSDK init hook error: %s", e)

    def register_extension(self, name: str, ext: Any) -> None:
        """Register an SDK extension."""
        self._extensions[name] = ext

    def get_extension(self, name: str) -> Optional[Any]:
        return self._extensions.get(name)

    def on(self, event: str, handler: Any) -> None:
        """Register an event hook."""
        self._hooks.setdefault(event, []).append(handler)

    async def invoke(self, extension: str, method: str, *args, **kwargs) -> Any:
        """Invoke a method on a registered extension."""
        ext = self._extensions.get(extension)
        if not ext:
            raise ValueError(f"Extension not found: {extension}")
        fn = getattr(ext, method, None)
        if not fn or not callable(fn):
            raise ValueError(f"Method not found: {extension}.{method}")
        if asyncio.iscoroutinefunction(fn):
            return await fn(*args, **kwargs)
        return fn(*args, **kwargs)

    def list_extensions(self) -> List[str]:
        return sorted(self._extensions.keys())

    @property
    def is_initialized(self) -> bool:
        return self._initialized


