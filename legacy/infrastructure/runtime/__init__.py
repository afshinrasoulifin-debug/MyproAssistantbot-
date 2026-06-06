
"""Runtime layer — execution environments for AI operations."""
try:
    from arki_project.infrastructure.runtime.ai_runtime import AIRuntime
    from arki_project.infrastructure.runtime.model_runtime import ModelRuntime
    from arki_project.infrastructure.runtime.assistant_runtime import AssistantRuntime
    from arki_project.infrastructure.runtime.edge_runtime import EdgeRuntime
    from arki_project.infrastructure.runtime.execution_runtime import ExecutionRuntime
    from arki_project.infrastructure.runtime.prompt_runtime import PromptRuntime
    from arki_project.infrastructure.runtime.context_runtime import ContextRuntime
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.runtime.ai_runtime import AIRuntime
        from infrastructure.runtime.model_runtime import ModelRuntime
        from infrastructure.runtime.assistant_runtime import AssistantRuntime
        from infrastructure.runtime.edge_runtime import EdgeRuntime
        from infrastructure.runtime.execution_runtime import ExecutionRuntime
        from infrastructure.runtime.prompt_runtime import PromptRuntime
        from infrastructure.runtime.context_runtime import ContextRuntime
    except (ImportError, ModuleNotFoundError):
        AIRuntime = None  # type: ignore
        ModelRuntime = None  # type: ignore
        AssistantRuntime = None  # type: ignore
        EdgeRuntime = None  # type: ignore
        ExecutionRuntime = None  # type: ignore
        PromptRuntime = None  # type: ignore
        ContextRuntime = None  # type: ignore


