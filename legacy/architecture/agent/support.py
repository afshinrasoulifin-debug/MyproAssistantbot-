
from __future__ import annotations
"""
architecture.agent.support — SupportAgent, IntegrationAgent
════════════════════════════════════════════════════════════
Support and integration agents.
Covers: support-agent, integration-agent
"""
import logging
from typing import Any, Dict

from .base import BaseAgent



logger = logging.getLogger(__name__)

class SupportAgent(BaseAgent):
    """Agent that handles user support queries and FAQ."""
    def __init__(self) -> None:
        super().__init__("support-agent")
        self._faq: Dict[str, str] = {}

    def add_faq(self, question: str, answer: str) -> None:
        self._faq[question.lower()] = answer

    async def act(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("query", "").lower()
        for q, a in self._faq.items():
            if q in query:
                return {"answer": a, "matched": q}
        return {"answer": None, "matched": None}

class IntegrationAgent(BaseAgent):
    """Agent that manages third-party integrations."""
    def __init__(self) -> None:
        super().__init__("integration-agent")
        self._integrations: Dict[str, dict] = {}

    def register(self, name: str, config: Dict[str, Any]) -> None:
        self._integrations[name] = {"config": config, "status": "registered"}

    async def act(self, context: Dict[str, Any]) -> Dict[str, Any]:
        action = context.get("action", "status")
        if action == "status":
            return {n: i["status"] for n, i in self._integrations.items()}
        return {"integrations": list(self._integrations.keys())}


