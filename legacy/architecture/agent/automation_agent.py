
from __future__ import annotations
"""
architecture.agent.automation_agent — AutomationAgent, MaintenanceAgent
═══════════════════════════════════════════════════════════════════════
Automation and maintenance agents.
Covers: automation-agent, maintenance-agent
"""
import logging, time
from typing import Any, Dict, List

from .base import BaseAgent

logger = logging.getLogger(__name__)

class AutomationAgent(BaseAgent):
    """Autonomous automation that triggers workflows based on conditions."""
    def __init__(self) -> None:
        super().__init__("automation-agent")
        self._rules: List[dict] = []

    def add_rule(self, condition, action, name: str = "") -> None:
        self._rules.append({"name": name, "condition": condition, "action": action})

    async def act(self, context: Dict[str, Any]) -> Dict[str, Any]:
        triggered = []
        for rule in self._rules:
            try:
                if rule["condition"](context):
                    import asyncio
                    result = rule["action"](context)
                    if asyncio.iscoroutine(result):
                        result = await result
                    triggered.append(rule["name"])
            except Exception as exc:
                logger.error("AutomationAgent rule %s error: %s", rule["name"], exc)
        return {"triggered": triggered}

class MaintenanceAgent(BaseAgent):
    """Periodic maintenance tasks agent."""
    def __init__(self) -> None:
        super().__init__("maintenance-agent")
        self._tasks: List[dict] = []

    def add_task(self, name: str, fn, interval_s: float = 3600) -> None:
        self._tasks.append({"name": name, "fn": fn, "interval_s": interval_s, "last_run": 0})

    async def act(self, context: Dict[str, Any]) -> Dict[str, Any]:
        now = time.time()
        ran = []
        for task in self._tasks:
            if (now - task["last_run"]) >= task["interval_s"]:
                try:
                    import asyncio
                    r = task["fn"]()
                    if asyncio.iscoroutine(r):
                        r = await r
                    task["last_run"] = now
                    ran.append(task["name"])
                except Exception as exc:
                    logger.error("Maintenance task %s error: %s", task["name"], exc)
        return {"ran": ran}


