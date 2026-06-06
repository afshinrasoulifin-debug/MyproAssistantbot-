
"""Bridge layer — connect disparate systems."""
try:
    from arki_project.infrastructure.bridges.ai_bridge import AIBridge
    from arki_project.infrastructure.bridges.runtime_bridge import InfraRuntimeBridge
    from arki_project.infrastructure.bridges.cloud_bridge import CloudBridge
    from arki_project.infrastructure.bridges.provider_bridge import InfraProviderBridge
    from arki_project.infrastructure.bridges.websocket_bridge import InfraWebSocketBridge
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.bridges.ai_bridge import AIBridge
        from infrastructure.bridges.runtime_bridge import InfraRuntimeBridge
        from infrastructure.bridges.cloud_bridge import CloudBridge
        from infrastructure.bridges.provider_bridge import InfraProviderBridge
        from infrastructure.bridges.websocket_bridge import InfraWebSocketBridge
    except (ImportError, ModuleNotFoundError):
        AIBridge = None  # type: ignore
        InfraRuntimeBridge = None  # type: ignore
        CloudBridge = None  # type: ignore
        InfraProviderBridge = None  # type: ignore
        InfraWebSocketBridge = None  # type: ignore


