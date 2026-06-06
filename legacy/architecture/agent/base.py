
from __future__ import annotations
"""
architecture.agent.base — BaseAgent, AgentState
═══════════════════════════════════════════════
Abstract base for all autonomous agents.
Covers: agent, node, observer, watcher
"""
import logging, time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Optional



logger = logging.getLogger(__name__)

class AgentState(Enum):
    IDLE = auto(); ACTIVE = auto(); PAUSED = auto()
    ERROR = auto(); STOPPED = auto()

@dataclass
class AgentMetrics:
    actions_taken: int = 0
    errors: int = 0
    last_action: float = 0
    total_runtime_s: float = 0

class BaseAgent(ABC):
    """Abstract autonomous agent with lifecycle and metrics."""
    def __init__(self, name: str) -> None:
        self.name = name
        self.state = AgentState.IDLE
        self.metrics = AgentMetrics()
        self._start_time: Optional[float] = None

    @abstractmethod
    async def act(self, context: Dict[str, Any]) -> Any:
        raise NotImplementedError('Subclass must implement act')

    async def start(self) -> None:
        self.state = AgentState.ACTIVE
        self._start_time = time.time()
        logger.info("Agent %s started", self.name)

    async def stop(self) -> None:
        if self._start_time:
            self.metrics.total_runtime_s += time.time() - self._start_time
        self.state = AgentState.STOPPED
        logger.info("Agent %s stopped", self.name)

    async def safe_act(self, context: Dict[str, Any]) -> Any:
        try:
            result = await self.act(context)
            self.metrics.actions_taken += 1
            self.metrics.last_action = time.time()
            return result
        except Exception as exc:
            self.metrics.errors += 1
            self.state = AgentState.ERROR
            logger.error("Agent %s error: %s", self.name, exc)
            return None

    @property
    def status(self) -> Dict[str, Any]:
        return {"name": self.name, "state": self.state.name, **vars(self.metrics)}


