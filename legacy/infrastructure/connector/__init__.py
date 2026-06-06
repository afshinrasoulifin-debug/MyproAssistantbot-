
"""Connector layer — connect to external services."""
try:
    from arki_project.infrastructure.connector.ai_connector import AIConnector
    from arki_project.infrastructure.connector.provider_connector import ProviderConnector
    from arki_project.infrastructure.connector.service_connector import ServiceConnector
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.connector.ai_connector import AIConnector
        from infrastructure.connector.provider_connector import ProviderConnector
        from infrastructure.connector.service_connector import ServiceConnector
    except (ImportError, ModuleNotFoundError):
        AIConnector = None  # type: ignore
        ProviderConnector = None  # type: ignore
        ServiceConnector = None  # type: ignore


