
from __future__ import annotations
"""
architecture.bridge.core — BridgeCore, SystemBridge, NativeBridge
═══════════════════════════════════════════════════════════════
Core bridge infrastructure for connecting subsystems.
Covers: bridge-core, system-bridge, native-bridge, bridge
"""
import logging
from typing import Any, Callable, Dict, List



logger = logging.getLogger(__name__)

class BridgeCore:
    """Core bridge connecting two subsystems."""
    def __init__(self, source: str, target: str) -> None:
        self.source = source
        self.target = target
        self._transformers: List[Callable] = []
        self._message_count = 0

    def add_transformer(self, fn: Callable[[Any], Any]) -> None:
        self._transformers.append(fn)

    def transfer(self, data: Any) -> Any:
        result = data
        for transformer in self._transformers:
            result = transformer(result)
        self._message_count += 1
        return result

    @property
    def stats(self) -> Dict[str, Any]:
        return {"source": self.source, "target": self.target,
                "messages": self._message_count, "transformers": len(self._transformers)}

class SystemBridge(BridgeCore):
    """Bridge between system-level components."""
    def __init__(self, source: str = "system", target: str = "application") -> None:
        super().__init__(source, target)
        self._bidirectional = True

    def transfer_back(self, data: Any) -> Any:
        self._message_count += 1
        return data

class NativeBridge(BridgeCore):
    """Bridge to native OS or platform features."""
    def __init__(self) -> None:
        super().__init__("native", "application")
        self._capabilities: Dict[str, bool] = {}

    def check_capability(self, name: str) -> bool:
        return self._capabilities.get(name, False)

    def register_capability(self, name: str, available: bool = True) -> None:
        self._capabilities[name] = available


