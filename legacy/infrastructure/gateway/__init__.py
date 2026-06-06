
"""Gateway layer — unified entry points for AI services."""
try:
    from arki_project.infrastructure.gateway.ai_gateway import AIGateway
    from arki_project.infrastructure.gateway.proxy_gateway import ProxyGateway
    from arki_project.infrastructure.gateway.unified_gateway import UnifiedGateway
    from arki_project.infrastructure.gateway.smart_gateway import SmartGateway
    from arki_project.infrastructure.gateway.runtime_gateway import RuntimeGateway
    from arki_project.infrastructure.gateway.cloud_gateway import CloudGateway
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.gateway.ai_gateway import AIGateway
        from infrastructure.gateway.proxy_gateway import ProxyGateway
        from infrastructure.gateway.unified_gateway import UnifiedGateway
        from infrastructure.gateway.smart_gateway import SmartGateway
        from infrastructure.gateway.runtime_gateway import RuntimeGateway
        from infrastructure.gateway.cloud_gateway import CloudGateway
    except (ImportError, ModuleNotFoundError):
        AIGateway = None  # type: ignore
        ProxyGateway = None  # type: ignore
        UnifiedGateway = None  # type: ignore
        SmartGateway = None  # type: ignore
        RuntimeGateway = None  # type: ignore
        CloudGateway = None  # type: ignore


