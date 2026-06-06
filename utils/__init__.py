
from __future__ import annotations

"""Core utility package initializer.

The initializer intentionally avoids eager imports of dependency-heavy modules.
Use direct submodule imports or the package attributes below, which resolve
lazily to preserve backward compatibility without making every utility import
load the full AI client stack.
"""

__all__ = ["AIClient", "store", "get_client", "TaskRunner"]


def __getattr__(name: str):
    if name == "AIClient":
        from arki_project.utils.ai_client import AIClient
        return AIClient
    if name == "store":
        from arki_project.utils.data_store import store
        return store
    if name == "get_client":
        from arki_project.utils.http_pool import get_client
        return get_client
    if name == "TaskRunner":
        try:
            from arki_project.utils.task_runner import WorkflowExecutor as TaskRunner
        except ImportError:
            TaskRunner = None
        return TaskRunner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


