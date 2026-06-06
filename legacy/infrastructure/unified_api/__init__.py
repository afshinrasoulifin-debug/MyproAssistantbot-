
"""Unified API — single API surface for all AI operations."""
try:
    from arki_project.infrastructure.unified_api.api_surface import UnifiedAPISurface
    from arki_project.infrastructure.unified_api.ai_hub import AIHub
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.unified_api.api_surface import UnifiedAPISurface
        from infrastructure.unified_api.ai_hub import AIHub
    except (ImportError, ModuleNotFoundError):
        UnifiedAPISurface = None  # type: ignore
        AIHub = None  # type: ignore


