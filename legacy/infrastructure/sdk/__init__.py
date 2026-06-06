
"""SDK — Developer SDK for extending the AI system."""
try:
    from arki_project.infrastructure.sdk.ai_sdk import AISDK
    from arki_project.infrastructure.sdk.plugin_sdk import PluginSDK
    from arki_project.infrastructure.sdk.extension_sdk import ExtensionSDK
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.sdk.ai_sdk import AISDK
        from infrastructure.sdk.plugin_sdk import PluginSDK
        from infrastructure.sdk.extension_sdk import ExtensionSDK
    except (ImportError, ModuleNotFoundError):
        AISDK = None  # type: ignore
        PluginSDK = None  # type: ignore
        ExtensionSDK = None  # type: ignore


