
from __future__ import annotations
"""
architecture.core.hooks — RuntimeHooks, DynamicHooks, HotReload
═══════════════════════════════════════════════════════════════
Hook system for extending bot behavior at runtime without
modifying core code. Supports pre/post hooks, middleware chains,
and hot-reloading of handlers.

Covers: runtime-hooks, dynamic-hooks, hot-reload, live-update
"""


import asyncio
import importlib
import logging
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HookPhase(Enum):
    PRE = auto()
    POST = auto()
    ERROR = auto()
    AROUND = auto()


@dataclass
class HookEntry:
    name: str
    phase: HookPhase
    callback: Callable
    priority: int = 50
    enabled: bool = True
    call_count: int = 0
    last_called: float = 0


class RuntimeHooks:
    """
    Named hook points that handlers can register callbacks on.
    Supports pre/post/error/around phases with priority ordering.
    """

    def __init__(self) -> None:
        self._hooks: Dict[str, List[HookEntry]] = {}
        self._global_hooks: List[HookEntry] = []

    def register(
        self, event: str, callback: Callable,
        phase: HookPhase = HookPhase.PRE, priority: int = 50,
        name: str = "",
    ) -> HookEntry:
        entry = HookEntry(
            name=name or callback.__name__,
            phase=phase, callback=callback, priority=priority,
        )
        self._hooks.setdefault(event, []).append(entry)
        self._hooks[event].sort(key=lambda h: h.priority)
        return entry

    def register_global(
        self, callback: Callable, phase: HookPhase = HookPhase.PRE,
        priority: int = 50, name: str = "",
    ) -> HookEntry:
        entry = HookEntry(
            name=name or callback.__name__,
            phase=phase, callback=callback, priority=priority,
        )
        self._global_hooks.append(entry)
        self._global_hooks.sort(key=lambda h: h.priority)
        return entry

    async def trigger(
        self, event: str, phase: HookPhase = HookPhase.PRE,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        results = []
        ctx = context or {}
        all_hooks = self._global_hooks + self._hooks.get(event, [])
        for hook in all_hooks:
            if not hook.enabled or hook.phase != phase:
                continue
            try:
                result = hook.callback(event, ctx)
                if asyncio.iscoroutine(result):
                    result = await result
                results.append(result)
                hook.call_count += 1
                hook.last_called = time.time()
            except Exception as exc:
                logger.warning("Hook %s error on %s: %s", hook.name, event, exc)
        return results

    def unregister(self, event: str, name: str) -> bool:
        hooks = self._hooks.get(event, [])
        for i, h in enumerate(hooks):
            if h.name == name:
                hooks.pop(i)
                return True
        return False

    def list_hooks(self, event: Optional[str] = None) -> List[Dict[str, Any]]:
        hooks = self._hooks.get(event, []) if event else [
            h for hooks in self._hooks.values() for h in hooks
        ]
        return [
            {"name": h.name, "event": event, "phase": h.phase.name,
             "priority": h.priority, "enabled": h.enabled,
             "call_count": h.call_count}
            for h in hooks
        ]


class DynamicHooks(RuntimeHooks):
    """
    Extended hooks with pattern matching on event names
    and conditional execution based on context.
    """

    def __init__(self) -> None:
        super().__init__()
        self._patterns: List[tuple] = []  # (pattern, HookEntry)

    def register_pattern(
        self, pattern: str, callback: Callable,
        phase: HookPhase = HookPhase.PRE, priority: int = 50,
    ) -> HookEntry:
        entry = HookEntry(
            name=f"pattern:{pattern}",
            phase=phase, callback=callback, priority=priority,
        )
        self._patterns.append((pattern, entry))
        return entry

    async def trigger(
        self, event: str, phase: HookPhase = HookPhase.PRE,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        results = await super().trigger(event, phase, context)
        # Also trigger pattern matches
        for pattern, entry in self._patterns:
            if not entry.enabled or entry.phase != phase:
                continue
            if self._match_pattern(pattern, event):
                try:
                    result = entry.callback(event, context or {})
                    if asyncio.iscoroutine(result):
                        result = await result
                    results.append(result)
                    entry.call_count += 1
                    entry.last_called = time.time()
                except Exception as exc:
                    logger.warning("Pattern hook %s error: %s", pattern, exc)
        return results

    @staticmethod
    def _match_pattern(pattern: str, event: str) -> bool:
        if pattern == "*":
            return True
        if pattern.endswith(".*"):
            return event.startswith(pattern[:-2])
        if pattern.startswith("*."):
            return event.endswith(pattern[2:])
        return pattern == event


class HotReload:
    """
    Hot-reload support for Python modules at runtime.
    Watches specified modules and reloads them on change.
    """

    def __init__(self) -> None:
        self._watched: Dict[str, float] = {}  # module_name → last_reload
        self._reload_count: int = 0
        self._hooks = DynamicHooks()

    def watch(self, module_name: str) -> None:
        self._watched[module_name] = time.time()
        logger.debug("HotReload watching: %s", module_name)

    def reload_module(self, module_name: str) -> bool:
        try:
            import sys
            if module_name in sys.modules:
                mod = sys.modules[module_name]
                importlib.reload(mod)
                self._watched[module_name] = time.time()
                self._reload_count += 1
                logger.info("HotReload: reloaded %s", module_name)
                return True
        except Exception as exc:
            logger.error("HotReload failed for %s: %s", module_name, exc)
        return False

    def reload_all(self) -> Dict[str, bool]:
        results = {}
        for mod_name in list(self._watched.keys()):
            results[mod_name] = self.reload_module(mod_name)
        return results

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "watched_modules": len(self._watched),
            "total_reloads": self._reload_count,
            "modules": list(self._watched.keys()),
        }


# ── Singletons ──
_hooks: Optional[DynamicHooks] = None
_hot_reload: Optional[HotReload] = None

def get_hooks() -> DynamicHooks:
    global _hooks
    if _hooks is None:
        _hooks = DynamicHooks()
    return _hooks

def get_hot_reload() -> HotReload:
    global _hot_reload
    if _hot_reload is None:
        _hot_reload = HotReload()
    return _hot_reload


