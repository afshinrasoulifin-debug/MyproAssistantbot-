
from __future__ import annotations
"""
architecture.core.runtime — RuntimeCore, ExecutionContext, RuntimeContext
═════════════════════════════════════════════════════════════════════════
Central runtime that manages the bot lifecycle, provides execution
contexts for every handler call, and tracks runtime state.

Covers: core, runtime, runtime-core, execution-context, runtime-context,
        embedded-runtime, isolated-runtime, internal-runtime,
        experimental-runtime, developer-runtime
"""


import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional



logger = logging.getLogger(__name__)


class RuntimePhase(Enum):
    INIT = auto()
    STARTING = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPING = auto()
    STOPPED = auto()
    ERROR = auto()


class RuntimeMode(Enum):
    EMBEDDED = "embedded"
    ISOLATED = "isolated"
    INTERNAL = "internal"
    EXPERIMENTAL = "experimental"
    DEVELOPER = "developer"


@dataclass
class ExecutionContext:
    """Per-request execution context for handler calls."""
    context_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    user_id: int = 0
    command: str = ""
    handler: str = ""
    start_time: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_context: Optional[str] = None
    _results: List[Any] = field(default_factory=list)

    @property
    def elapsed(self) -> float:
        return time.time() - self.start_time

    def set(self, key: str, value: Any) -> None:
        self.metadata[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default)

    def add_result(self, result: Any) -> None:
        self._results.append(result)

    def child(self, handler: str = "") -> ExecutionContext:
        return ExecutionContext(
            user_id=self.user_id,
            command=self.command,
            handler=handler or self.handler,
            parent_context=self.context_id,
        )


@dataclass
class RuntimeContext:
    """Global runtime context — shared across all handlers."""
    runtime_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    mode: RuntimeMode = RuntimeMode.INTERNAL
    phase: RuntimePhase = RuntimePhase.INIT
    boot_time: float = field(default_factory=time.time)
    config: Dict[str, Any] = field(default_factory=dict)
    _active_contexts: Dict[str, ExecutionContext] = field(default_factory=dict)
    _stats: Dict[str, int] = field(default_factory=lambda: {
        "total_requests": 0,
        "active_requests": 0,
        "errors": 0,
        "completed": 0,
    })

    @property
    def uptime(self) -> float:
        return time.time() - self.boot_time

    def create_execution_context(
        self, user_id: int, command: str, handler: str
    ) -> ExecutionContext:
        ctx = ExecutionContext(
            user_id=user_id, command=command, handler=handler
        )
        self._active_contexts[ctx.context_id] = ctx
        self._stats["total_requests"] += 1
        self._stats["active_requests"] += 1
        return ctx

    def complete_context(self, ctx: ExecutionContext) -> float:
        elapsed = ctx.elapsed
        self._active_contexts.pop(ctx.context_id, None)
        self._stats["active_requests"] -= 1
        self._stats["completed"] += 1
        return elapsed

    def error_context(self, ctx: ExecutionContext) -> None:
        self._active_contexts.pop(ctx.context_id, None)
        self._stats["active_requests"] -= 1
        self._stats["errors"] += 1

    @property
    def stats(self) -> Dict[str, Any]:
        return {**self._stats, "uptime_s": round(self.uptime, 1)}


class RuntimeCore:
    """
    Central runtime manager for the bot.

    Manages lifecycle phases, execution contexts, shutdown hooks,
    and periodic background tasks.
    """

    def __init__(self, mode: RuntimeMode = RuntimeMode.INTERNAL) -> None:
        self.context = RuntimeContext(mode=mode)
        self._shutdown_hooks: List[Callable] = []
        self._startup_hooks: List[Callable] = []
        self._background_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        logger.info("RuntimeCore initialized [%s] mode=%s", self.context.runtime_id, mode.value)

    @property
    def phase(self) -> RuntimePhase:
        return self.context.phase

    @property
    def is_running(self) -> bool:
        return self.context.phase == RuntimePhase.RUNNING

    def on_startup(self, hook: Callable) -> Callable:
        self._startup_hooks.append(hook)
        return hook

    def on_shutdown(self, hook: Callable) -> Callable:
        self._shutdown_hooks.append(hook)
        return hook

    async def start(self) -> None:
        self.context.phase = RuntimePhase.STARTING
        for hook in self._startup_hooks:
            try:
                result = hook()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logger.error("Startup hook failed: %s", exc)
        self.context.phase = RuntimePhase.RUNNING
        logger.info("RuntimeCore RUNNING [uptime: %.1fs]", self.context.uptime)

    async def stop(self) -> None:
        self.context.phase = RuntimePhase.STOPPING
        # Cancel background tasks
        for name, task in self._background_tasks.items():
            task.cancel()
            logger.debug("Cancelled background task: %s", name)
        # Run shutdown hooks in reverse
        for hook in reversed(self._shutdown_hooks):
            try:
                result = hook()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logger.error("Shutdown hook failed: %s", exc)
        self.context.phase = RuntimePhase.STOPPED
        logger.info("RuntimeCore STOPPED [uptime: %.1fs]", self.context.uptime)

    def execute(self, user_id: int, command: str, handler: str) -> ExecutionContext:
        return self.context.create_execution_context(user_id, command, handler)

    def complete(self, ctx: ExecutionContext) -> float:
        return self.context.complete_context(ctx)

    def fail(self, ctx: ExecutionContext) -> None:
        self.context.error_context(ctx)

    def schedule_background(
        self, name: str, coro_func: Callable, interval_s: float = 300
    ) -> None:
        async def _loop():
            while self.is_running:
                try:
                    await coro_func()
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.error("Background task %s error: %s", name, exc)
                await asyncio.sleep(interval_s)

        self._background_tasks[name] = asyncio.ensure_future(_loop())

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "runtime_id": self.context.runtime_id,
            "mode": self.context.mode.value,
            "phase": self.context.phase.name,
            **self.context.stats,
            "background_tasks": list(self._background_tasks.keys()),
        }


# ── Singleton ──
_runtime: Optional[RuntimeCore] = None


def get_runtime(mode: RuntimeMode = RuntimeMode.INTERNAL) -> RuntimeCore:
    global _runtime
    if _runtime is None:
        _runtime = RuntimeCore(mode=mode)
    return _runtime


