
"""Provider layer — multi-provider AI routing with fallback, shadow, pool."""
try:
    from arki_project.infrastructure.providers.provider_pool import ProviderPool
    from arki_project.infrastructure.providers.smart_provider import SmartProvider
    from arki_project.infrastructure.providers.fallback_provider import FallbackProvider
    from arki_project.infrastructure.providers.shadow_provider import ShadowProvider
    from arki_project.infrastructure.providers.provider_router import ProviderRouter
    from arki_project.infrastructure.providers.multi_provider import MultiProvider
    from arki_project.infrastructure.providers.dynamic_provider import DynamicProvider
    from arki_project.infrastructure.providers.auto_provider import AutoProvider
    from arki_project.infrastructure.providers.runtime_provider import RuntimeProvider
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.providers.provider_pool import ProviderPool
        from infrastructure.providers.smart_provider import SmartProvider
        from infrastructure.providers.fallback_provider import FallbackProvider
        from infrastructure.providers.shadow_provider import ShadowProvider
        from infrastructure.providers.provider_router import ProviderRouter
        from infrastructure.providers.multi_provider import MultiProvider
        from infrastructure.providers.dynamic_provider import DynamicProvider
        from infrastructure.providers.auto_provider import AutoProvider
        from infrastructure.providers.runtime_provider import RuntimeProvider
    except (ImportError, ModuleNotFoundError):
        ProviderPool = None  # type: ignore
        SmartProvider = None  # type: ignore
        FallbackProvider = None  # type: ignore
        ShadowProvider = None  # type: ignore
        ProviderRouter = None  # type: ignore
        MultiProvider = None  # type: ignore
        DynamicProvider = None  # type: ignore
        AutoProvider = None  # type: ignore
        RuntimeProvider = None  # type: ignore


