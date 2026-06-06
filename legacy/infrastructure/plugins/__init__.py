
"""Plugin/Extension system."""
try:
    from arki_project.infrastructure.plugins.plugin_system import InfraPluginSystem
    from arki_project.infrastructure.plugins.extension_system import ExtensionSystem
    from arki_project.infrastructure.plugins.module_system import ModuleSystem
    from arki_project.infrastructure.plugins.dynamic_loader import InfraDynamicLoader
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.plugins.plugin_system import InfraPluginSystem
        from infrastructure.plugins.extension_system import ExtensionSystem
        from infrastructure.plugins.module_system import ModuleSystem
        from infrastructure.plugins.dynamic_loader import InfraDynamicLoader
    except (ImportError, ModuleNotFoundError):
        InfraPluginSystem = None  # type: ignore
        ExtensionSystem = None  # type: ignore
        ModuleSystem = None  # type: ignore
        InfraDynamicLoader = None  # type: ignore


