
"""Adapter layer — adapt interfaces between components."""
try:
    from arki_project.infrastructure.adapters.ai_adapter import InfraAIAdapter
    from arki_project.infrastructure.adapters.model_adapter import ModelAdapter
    from arki_project.infrastructure.adapters.provider_adapter import InfraProviderAdapter
    from arki_project.infrastructure.adapters.runtime_adapter import InfraRuntimeAdapter
    from arki_project.infrastructure.adapters.proxy_adapter import ProxyAdapter
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.adapters.ai_adapter import InfraAIAdapter
        from infrastructure.adapters.model_adapter import ModelAdapter
        from infrastructure.adapters.provider_adapter import InfraProviderAdapter
        from infrastructure.adapters.runtime_adapter import InfraRuntimeAdapter
        from infrastructure.adapters.proxy_adapter import ProxyAdapter
    except (ImportError, ModuleNotFoundError):
        InfraAIAdapter = None  # type: ignore
        ModelAdapter = None  # type: ignore
        InfraProviderAdapter = None  # type: ignore
        InfraRuntimeAdapter = None  # type: ignore
        ProxyAdapter = None  # type: ignore


