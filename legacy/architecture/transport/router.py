
from __future__ import annotations
"""
architecture.transport.router — TaskRouter, CommandRouter, ActionRouter
═════════════════════════════════════════════════════════════════════
Route messages/tasks to appropriate handlers based on rules.
Covers: task-router, command-router, action-router
"""
import logging, re
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class TaskRouter:
    """Route tasks to handlers based on task type or pattern."""
    def __init__(self) -> None:
        self._routes: List[Tuple[str, Callable]] = []
        self._pattern_routes: List[Tuple[str, Callable]] = []
        self._default: Optional[Callable] = None

    def route(self, task_type: str, handler: Callable) -> None:
        self._routes.append((task_type, handler))

    def route_pattern(self, pattern: str, handler: Callable) -> None:
        self._pattern_routes.append((pattern, handler))

    def default(self, handler: Callable) -> None:
        self._default = handler

    def resolve(self, task_type: str) -> Optional[Callable]:
        for rt, handler in self._routes:
            if rt == task_type:
                return handler
        for pattern, handler in self._pattern_routes:
            if re.match(pattern, task_type):
                return handler
        return self._default

    async def dispatch(self, task_type: str, payload: Any) -> Any:
        handler = self.resolve(task_type)
        if handler is None:
            raise KeyError(f"No route for: {task_type}")
        import asyncio
        result = handler(payload)
        if asyncio.iscoroutine(result):
            result = await result
        return result

class CommandRouter(TaskRouter):
    """Route bot commands to handler functions."""
    def __init__(self) -> None:
        super().__init__()
        self._middleware: List[Callable] = []

    def use(self, middleware: Callable) -> None:
        self._middleware.append(middleware)

    async def dispatch(self, command: str, payload: Any) -> Any:
        import asyncio
        ctx = {"command": command, "payload": payload}
        for mw in self._middleware:
            result = mw(ctx)
            if asyncio.iscoroutine(result):
                result = await result
            if result is False:
                return None
        return await super().dispatch(command, payload)

class ActionRouter(TaskRouter):
    """Route actions with priority and fallback chains."""
    def __init__(self) -> None:
        super().__init__()
        self._fallbacks: Dict[str, List[Callable]] = {}

    def add_fallback(self, action: str, handler: Callable) -> None:
        self._fallbacks.setdefault(action, []).append(handler)

    async def dispatch(self, action: str, payload: Any) -> Any:
        import asyncio
        try:
            return await super().dispatch(action, payload)
        except Exception as primary_exc:
            for fallback in self._fallbacks.get(action, []):
                try:
                    result = fallback(payload)
                    if asyncio.iscoroutine(result):
                        result = await result
                    return result
                except Exception:
                    continue
            raise primary_exc


