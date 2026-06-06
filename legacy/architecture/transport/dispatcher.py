
from __future__ import annotations
"""
architecture.transport.dispatcher — Dispatcher, TaskDispatcher, CommandDispatcher, ActionDispatcher
═══════════════════════════════════════════════════════════════════════════════════════════════════
Dispatch messages to registered handlers with queue support.
Covers: dispatcher, task-dispatcher, command-dispatcher, action-dispatcher
"""
import asyncio, logging, time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional



logger = logging.getLogger(__name__)

@dataclass
class DispatchRecord:
    target: str
    payload: Any
    dispatched_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    success: bool = False
    error: Optional[str] = None

class Dispatcher:
    """Base dispatcher with handler registration and dispatch tracking."""
    def __init__(self) -> None:
        self._handlers: Dict[str, Callable] = {}
        self._history: List[DispatchRecord] = []

    def register(self, name: str, handler: Callable) -> None:
        self._handlers[name] = handler

    async def dispatch(self, name: str, payload: Any = None) -> Any:
        record = DispatchRecord(target=name, payload=payload)
        handler = self._handlers.get(name)
        if not handler:
            record.error = f"No handler: {name}"
            self._history.append(record)
            raise KeyError(record.error)
        try:
            result = handler(payload)
            if asyncio.iscoroutine(result):
                result = await result
            record.success = True
            record.completed_at = time.time()
            return result
        except Exception as exc:
            record.error = str(exc)
            raise
        finally:
            self._history.append(record)

    @property
    def stats(self) -> Dict[str, Any]:
        return {"handlers": list(self._handlers.keys()),
                "dispatched": len(self._history),
                "success": sum(1 for r in self._history if r.success)}

class TaskDispatcher(Dispatcher):
    """Dispatcher with async queue for task processing."""
    def __init__(self, max_concurrent: int = 10) -> None:
        super().__init__()
        self._queue: asyncio.Queue = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._processing = False

    async def enqueue(self, name: str, payload: Any = None) -> None:
        await self._queue.put((name, payload))

    async def process_queue(self) -> None:
        self._processing = True
        while self._processing:
            try:
                name, payload = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                async with self._semaphore:
                    await self.dispatch(name, payload)
            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                logger.error("TaskDispatcher error: %s", exc)

    def stop(self) -> None:
        self._processing = False

class CommandDispatcher(Dispatcher):
    """Dispatcher for Telegram bot commands with middleware."""
    def __init__(self) -> None:
        super().__init__()
        self._middleware: List[Callable] = []

    def use(self, middleware: Callable) -> None:
        self._middleware.append(middleware)

    async def dispatch(self, name: str, payload: Any = None) -> Any:
        for mw in self._middleware:
            result = mw(name, payload)
            if asyncio.iscoroutine(result):
                result = await result
            if result is False:
                return None
        return await super().dispatch(name, payload)

ActionDispatcher = Dispatcher


