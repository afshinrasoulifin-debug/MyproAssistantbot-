
"""
handlers/_command_dispatch.py — Shared command dispatch patterns
Reduces cyclomatic complexity in handler functions by centralizing:
- Safe import pattern
- Multi-branch dispatch
- Error-wrapped execution
"""
from __future__ import annotations
import logging
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


async def safe_import_call(
    module_path: str,
    func_name: str,
    *args: Any,
    fallback: Any = None,
    **kwargs: Any,
) -> Any:
    """Safely import and call a function, returning fallback on failure.
    
    Replaces the pattern:
        try:
            from X import Y
            result = await Y(...)
        except Exception:
            result = fallback
    """
    try:
        import importlib
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)
        if callable(func):
            result = func(*args, **kwargs)
            if hasattr(result, '__await__'):
                return await result
            return result
        return func
    except (ImportError, AttributeError) as exc:
        logger.debug("safe_import_call %s.%s: %s", module_path, func_name, exc)
        return fallback
    except Exception as exc:
        logger.warning("safe_import_call %s.%s error: %s", module_path, func_name, exc)
        return fallback


class CommandDispatcher:
    """Route sub-commands to handlers, reducing if/elif chains.
    
    Usage:
        dispatch = CommandDispatcher()
        dispatch.register("list", handle_list)
        dispatch.register("add", handle_add)
        dispatch.register("delete", handle_delete)
        result = await dispatch.execute(sub_command, message, *args)
    """

    def __init__(self, default_handler: Optional[Callable] = None):
        self._handlers: Dict[str, Callable] = {}
        self._default = default_handler
        self._aliases: Dict[str, str] = {}

    def register(self, command: str, handler: Callable, aliases: list = None) -> None:
        self._handlers[command] = handler
        if aliases:
            for alias in aliases:
                self._aliases[alias] = command

    async def execute(self, command: str, *args: Any, **kwargs: Any) -> Any:
        """Execute the matching handler for a command."""
        # Resolve aliases
        resolved = self._aliases.get(command, command)
        handler = self._handlers.get(resolved)

        if handler is None and self._default:
            handler = self._default

        if handler is None:
            return None

        try:
            result = handler(*args, **kwargs)
            if hasattr(result, '__await__'):
                return await result
            return result
        except Exception as exc:
            logger.error("Command '%s' error: %s", command, exc)
            raise


class ServiceInitializer:
    """Batch-initialize services with error isolation.
    
    Replaces chains of:
        try: service1 = ... except: ...
        try: service2 = ... except: ...
    """

    def __init__(self):
        self._services: list = []
        self._results: Dict[str, Any] = {}

    def add(self, name: str, init_func: Callable, *args: Any, **kwargs: Any) -> None:
        self._services.append((name, init_func, args, kwargs))

    async def init_all(self) -> Dict[str, Any]:
        """Initialize all services, logging failures but continuing."""
        for name, func, args, kwargs in self._services:
            try:
                result = func(*args, **kwargs)
                if hasattr(result, '__await__'):
                    result = await result
                self._results[name] = result
                logger.debug("✓ %s initialized", name)
            except Exception as exc:
                self._results[name] = None
                logger.warning("✗ %s failed: %s", name, exc)
        return self._results

    def get(self, name: str) -> Any:
        return self._results.get(name)


