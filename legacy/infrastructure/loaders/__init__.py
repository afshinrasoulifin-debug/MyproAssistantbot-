
"""Loader layer — dynamic loading of components."""
try:
    from arki_project.infrastructure.loaders.runtime_loader import InfraRuntimeLoader
    from arki_project.infrastructure.loaders.plugin_loader import InfraPluginLoader
    from arki_project.infrastructure.loaders.dynamic_loader import DynamicLoader
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.loaders.runtime_loader import InfraRuntimeLoader
        from infrastructure.loaders.plugin_loader import InfraPluginLoader
        from infrastructure.loaders.dynamic_loader import DynamicLoader
    except (ImportError, ModuleNotFoundError):
        InfraRuntimeLoader = None  # type: ignore
        InfraPluginLoader = None  # type: ignore
        DynamicLoader = None  # type: ignore


