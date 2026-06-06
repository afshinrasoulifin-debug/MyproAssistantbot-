
from __future__ import annotations
"""
architecture.control.controller — Controller, Coordinator, Supervisor, Operator
══════════════════════════════════════════════════════════════════════════════
Control structures for managing bot subsystems.
Covers: controller, coordinator, supervisor, operator
"""
import asyncio, logging
from typing import Any, Dict, Optional



logger = logging.getLogger(__name__)

class Controller:
    """Base controller managing a set of components."""
    def __init__(self, name: str) -> None:
        self.name = name
        self._components: Dict[str, Any] = {}
        self._active = False

    def register(self, name: str, component: Any) -> None:
        self._components[name] = component

    def get(self, name: str) -> Optional[Any]:
        return self._components.get(name)

    async def start(self) -> None:
        self._active = True
        for name, comp in self._components.items():
            if hasattr(comp, "start"):
                result = comp.start()
                if asyncio.iscoroutine(result):
                    await result
        logger.info("Controller %s started with %d components", self.name, len(self._components))

    async def stop(self) -> None:
        for name, comp in reversed(list(self._components.items())):
            if hasattr(comp, "stop"):
                result = comp.stop()
                if asyncio.iscoroutine(result):
                    await result
        self._active = False

    @property
    def status(self) -> Dict[str, Any]:
        return {"name": self.name, "active": self._active, "components": list(self._components.keys())}

class Coordinator(Controller):
    """Controller that coordinates between multiple controllers."""
    def __init__(self) -> None:
        super().__init__("coordinator")
        self._controllers: Dict[str, Controller] = {}

    def add_controller(self, controller: Controller) -> None:
        self._controllers[controller.name] = controller

    async def start_all(self) -> None:
        for ctrl in self._controllers.values():
            await ctrl.start()
        self._active = True

    async def stop_all(self) -> None:
        for ctrl in reversed(list(self._controllers.values())):
            await ctrl.stop()
        self._active = False

class Supervisor(Controller):
    """Controller with auto-restart and error recovery."""
    def __init__(self, name: str = "supervisor", max_restarts: int = 3) -> None:
        super().__init__(name)
        self._max_restarts = max_restarts
        self._restart_counts: Dict[str, int] = {}

    async def restart_component(self, name: str) -> bool:
        comp = self._components.get(name)
        if not comp:
            return False
        count = self._restart_counts.get(name, 0)
        if count >= self._max_restarts:
            logger.error("Component %s exceeded max restarts", name)
            return False
        try:
            if hasattr(comp, "stop"):
                await comp.stop() if asyncio.iscoroutine(comp.stop()) else comp.stop()
            if hasattr(comp, "start"):
                await comp.start() if asyncio.iscoroutine(comp.start()) else comp.start()
            self._restart_counts[name] = count + 1
            return True
        except Exception as exc:
            logger.error("Restart failed for %s: %s", name, exc)
            return False

class Operator(Controller):
    """High-level operator managing the entire system."""
    def __init__(self) -> None:
        super().__init__("operator")
        self._mode = "normal"

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        logger.info("Operator mode: %s", mode)

    @property
    def mode(self) -> str:
        return self._mode


