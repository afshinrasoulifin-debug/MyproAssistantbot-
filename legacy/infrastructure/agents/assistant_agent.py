
from __future__ import annotations
"""InfraAssistantAgent — Conversational assistant agent."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)



class InfraAssistantAgent:
    """InfraAssistantAgent — Conversational assistant agent."""

    def __init__(self, name: str = "assistant_agent", *, max_steps: int = 10) -> None:
        self.name = name
        self.max_steps = max_steps
        self._tools: Dict[str, Any] = {}
        self._history: List[Dict] = []
        self._state = "idle"
        logger.info("InfraAssistantAgent '%s' initialized (max_steps=%d)", name, max_steps)

    def register_tool(self, name: str, fn: Any) -> None:
        """Register a callable tool for the agent."""
        self._tools[name] = fn
        logger.debug("Agent '%s' registered tool: %s", self.name, name)

    async def execute(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a task with step-by-step reasoning."""
        self._state = "running"
        ctx = dict(context or {})
        ctx["task"] = task
        steps = []

        try:
            for step_num in range(1, self.max_steps + 1):
                step_result = await self._run_step(step_num, task, ctx)
                steps.append(step_result)
                if step_result.get("done"):
                    break
                ctx.update(step_result.get("updates", {}))

            result = {
                "agent": self.name,
                "task": task,
                "steps": len(steps),
                "status": "completed",
                "output": steps[-1].get("output") if steps else None,
            }
        except Exception as e:
            logger.error("Agent '%s' failed: %s", self.name, e)
            result = {"agent": self.name, "task": task, "status": "error", "error": str(e)}
        finally:
            self._state = "idle"

        self._history.append(result)
        return result

    async def _run_step(self, step_num: int, task: str, ctx: dict) -> dict:
        """Execute a single agent step."""
        logger.debug("Agent '%s' step %d", self.name, step_num)
        return {"step": step_num, "done": True, "output": f"Completed: {task}"}

    @property
    def state(self) -> str:
        return self._state

    @property
    def tools(self) -> List[str]:
        return list(self._tools.keys())

    def get_history(self, limit: int = 10) -> List[Dict]:
        return self._history[-limit:]


