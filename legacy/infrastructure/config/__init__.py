
"""Config layer — dynamic configuration."""
try:
    from arki_project.infrastructure.config.dynamic_config import DynamicConfig
    from arki_project.infrastructure.config.remote_config import InfraRemoteConfig
    from arki_project.infrastructure.config.provider_config import InfraProviderConfig
    from arki_project.infrastructure.config.runtime_config import InfraRuntimeConfig
    from arki_project.infrastructure.config.feature_flags import InfraFeatureFlags
    from arki_project.infrastructure.config.experimental_flags import ExperimentalFlags
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.config.dynamic_config import DynamicConfig
        from infrastructure.config.remote_config import InfraRemoteConfig
        from infrastructure.config.provider_config import InfraProviderConfig
        from infrastructure.config.runtime_config import InfraRuntimeConfig
        from infrastructure.config.feature_flags import InfraFeatureFlags
        from infrastructure.config.experimental_flags import ExperimentalFlags
    except (ImportError, ModuleNotFoundError):
        DynamicConfig = None  # type: ignore
        InfraRemoteConfig = None  # type: ignore
        InfraProviderConfig = None  # type: ignore
        InfraRuntimeConfig = None  # type: ignore
        InfraFeatureFlags = None  # type: ignore
        ExperimentalFlags = None  # type: ignore


