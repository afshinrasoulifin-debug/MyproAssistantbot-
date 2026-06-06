
from __future__ import annotations
"""
architecture.monitor.console — RuntimeConsole, AdminConsole, DeveloperConsole,
                               ControlPanel, AdminPanel, OperationsPanel, OrchestrationPanel
═══════════════════════════════════════════════════════════════════════════════════════════
Console and panel interfaces for monitoring and management.
Covers: runtime-console, admin-console, developer-console, internal-console,
        control-panel, admin-panel, operations-panel, orchestration-panel,
        console, terminal, shell
"""
import logging, time
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)

class RuntimeConsole:
    """Runtime console for system status and commands."""
    def __init__(self) -> None:
        self._commands: Dict[str, Callable] = {}
        self._output: List[str] = []

    def register_command(self, name: str, handler: Callable) -> None:
        self._commands[name] = handler

    async def execute(self, command: str, *args) -> str:
        handler = self._commands.get(command)
        if not handler:
            return f"Unknown command: {command}"
        try:
            import asyncio
            result = handler(*args)
            if asyncio.iscoroutine(result):
                result = await result
            output = str(result)
            self._output.append(f"[{time.strftime('%H:%M:%S')}] {command}: {output}")
            return output
        except Exception as exc:
            return f"Error: {exc}"

    def available_commands(self) -> List[str]:
        return list(self._commands.keys())

    @property
    def history(self) -> List[str]:
        return list(self._output)

class AdminConsole(RuntimeConsole):
    """Console with admin privileges for system management."""
    def __init__(self) -> None:
        super().__init__()
        self._admin_log: List[Dict[str, Any]] = []
        # Register default admin commands
        self.register_command("status", lambda: "System running")
        self.register_command("health", lambda: "All systems healthy")

    async def execute(self, command: str, *args) -> str:
        self._admin_log.append({"command": command, "args": args, "time": time.time()})
        return await super().execute(command, *args)

class DeveloperConsole(RuntimeConsole):
    """Console with developer tools and debugging."""
    def __init__(self) -> None:
        super().__init__()
        self._debug_mode = False
        self.register_command("debug", self._toggle_debug)
        self.register_command("inspect", self._inspect)

    def _toggle_debug(self) -> str:
        self._debug_mode = not self._debug_mode
        return f"Debug mode: {self._debug_mode}"

    def _inspect(self, target: str = "") -> str:
        return f"Inspect: {target or '(no target)'}"

class ControlPanel:
    """High-level control panel aggregating multiple consoles."""
    def __init__(self) -> None:
        self._sections: Dict[str, RuntimeConsole] = {}
        self._metrics: Dict[str, Any] = {}

    def add_section(self, name: str, console: RuntimeConsole) -> None:
        self._sections[name] = console

    def set_metric(self, name: str, value: Any) -> None:
        self._metrics[name] = value

    def dashboard(self) -> Dict[str, Any]:
        return {
            "sections": list(self._sections.keys()),
            "metrics": dict(self._metrics),
            "time": time.time(),
        }

AdminPanel = ControlPanel
OperationsPanel = ControlPanel
OrchestrationPanel = ControlPanel


