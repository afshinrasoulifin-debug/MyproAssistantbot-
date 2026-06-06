
from __future__ import annotations
"""
AIHub — Central hub connecting all AI subsystems.
"""
import logging
from typing import Any, Dict



logger = logging.getLogger(__name__)

class AIHub:
    """Central hub that connects providers, gateways, engines, and runtimes."""

    def __init__(self) -> None:
        self._components: Dict[str, Any] = {}
        self._initialized = False

    def register(self, name: str, component: Any) -> Any:
        self._components[name] = component

    def get(self, name: str) -> Any:
        return self._components.get(name)

    async def initialize(self) -> Any:
        logger.info("AIHub: initializing %d components", len(self._components))
        for name, comp in self._components.items():
            if hasattr(comp, 'start'):
                try:
                    await comp.start()
                except Exception as e:
                    logger.warning("AIHub: %s start failed: %s", name, e)
        self._initialized = True

    @property
    def status(self) -> Dict[str, str]:
        return {name: "active" for name in self._components}


