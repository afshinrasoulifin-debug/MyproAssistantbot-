
"""
tg_bot/infrastructure — Enterprise Infrastructure Layer v9.8.6
═══════════════════════════════════════════════════════════════
Complete multi-layer infrastructure for AI operations.
"""
try:
    from arki_project.infrastructure.registry import InfraRegistry
    from arki_project.infrastructure.boot import boot_infrastructure, get_infra
    from arki_project.infrastructure.api.api_builder import APIBuilderAgent, get_api_builder
except ImportError:
    # Fallback for direct imports (test environment / standalone usage)
    try:
        from infrastructure.registry import InfraRegistry
        from infrastructure.boot import boot_infrastructure, get_infra
        from infrastructure.api.api_builder import APIBuilderAgent, get_api_builder
    except ImportError:
        InfraRegistry = None  # type: ignore
        boot_infrastructure = None  # type: ignore
        get_infra = None  # type: ignore
        APIBuilderAgent = None  # type: ignore
        get_api_builder = None  # type: ignore

__all__ = [
    "InfraRegistry",
    "boot_infrastructure",
    "get_infra",
    "APIBuilderAgent",
    "get_api_builder",
]


