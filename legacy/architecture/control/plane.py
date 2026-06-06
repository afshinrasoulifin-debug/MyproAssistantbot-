
from __future__ import annotations
"""
architecture.control.plane — ControlPlane, OrchestrationLayer, ExecutionLayer,
                             IntegrationLayer, PlatformLayer, RuntimeLayer
═══════════════════════════════════════════════════════════════════════════════
Abstraction layers for the architecture.
Covers: control-plane, orchestration-layer, execution-layer, integration-layer,
        platform-layer, runtime-layer
"""
import logging
from typing import Any, Dict, List, Optional



logger = logging.getLogger(__name__)

class ArchitectureLayer:
    """Base architecture layer with dependency tracking."""
    def __init__(self, name: str, level: int) -> None:
        self.name = name
        self.level = level
        self._dependencies: List[str] = []
        self._components: Dict[str, Any] = {}

    def depends_on(self, layer_name: str) -> None:
        self._dependencies.append(layer_name)

    def register(self, name: str, component: Any) -> None:
        self._components[name] = component

    def get(self, name: str) -> Optional[Any]:
        return self._components.get(name)

    @property
    def info(self) -> Dict[str, Any]:
        return {"name": self.name, "level": self.level,
                "components": list(self._components.keys()),
                "dependencies": self._dependencies}

class ControlPlane(ArchitectureLayer):
    """Top-level control plane managing all layers."""
    def __init__(self) -> None:
        super().__init__("control-plane", 0)
        self._layers: Dict[str, ArchitectureLayer] = {}

    def add_layer(self, layer: ArchitectureLayer) -> None:
        self._layers[layer.name] = layer

    def get_layer(self, name: str) -> Optional[ArchitectureLayer]:
        return self._layers.get(name)

    def topology(self) -> List[Dict[str, Any]]:
        return sorted([l.info for l in self._layers.values()], key=lambda x: x["level"])

class RuntimeLayer(ArchitectureLayer):
    def __init__(self) -> None:
        super().__init__("runtime", 1)

class ExecutionLayer(ArchitectureLayer):
    def __init__(self) -> None:
        super().__init__("execution", 2)
        self.depends_on("runtime")

class OrchestrationLayer(ArchitectureLayer):
    def __init__(self) -> None:
        super().__init__("orchestration", 3)
        self.depends_on("execution")

class IntegrationLayer(ArchitectureLayer):
    def __init__(self) -> None:
        super().__init__("integration", 4)
        self.depends_on("orchestration")

class PlatformLayer(ArchitectureLayer):
    def __init__(self) -> None:
        super().__init__("platform", 5)
        self.depends_on("integration")


