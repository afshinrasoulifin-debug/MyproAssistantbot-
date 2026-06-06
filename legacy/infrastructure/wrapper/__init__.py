
"""Wrapper layer — convenient wrappers for complex subsystems."""
try:
    from arki_project.infrastructure.wrapper.ai_wrapper import AIWrapper
    from arki_project.infrastructure.wrapper.provider_wrapper import ProviderWrapper
    from arki_project.infrastructure.wrapper.model_wrapper import ModelWrapper
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.wrapper.ai_wrapper import AIWrapper
        from infrastructure.wrapper.provider_wrapper import ProviderWrapper
        from infrastructure.wrapper.model_wrapper import ModelWrapper
    except (ImportError, ModuleNotFoundError):
        AIWrapper = None  # type: ignore
        ProviderWrapper = None  # type: ignore
        ModelWrapper = None  # type: ignore


