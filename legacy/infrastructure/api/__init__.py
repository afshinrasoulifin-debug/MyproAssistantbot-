
"""API layer — internal and unified API surfaces + API Builder Agent."""
try:
    from arki_project.infrastructure.api.unified_api import UnifiedAPI
    from arki_project.infrastructure.api.internal_api import InternalAPI
    from arki_project.infrastructure.api.transport_api import TransportAPI
    from arki_project.infrastructure.api.runtime_api import RuntimeAPI
    from arki_project.infrastructure.api.api_builder import APIBuilderAgent, get_api_builder
except ImportError:
    try:
        from infrastructure.api.unified_api import UnifiedAPI
        from infrastructure.api.internal_api import InternalAPI
        from infrastructure.api.transport_api import TransportAPI
        from infrastructure.api.runtime_api import RuntimeAPI
        from infrastructure.api.api_builder import APIBuilderAgent, get_api_builder
    except ImportError:
        UnifiedAPI = None  # type: ignore
        InternalAPI = None  # type: ignore
        TransportAPI = None  # type: ignore
        RuntimeAPI = None  # type: ignore
        APIBuilderAgent = None  # type: ignore
        get_api_builder = None  # type: ignore


