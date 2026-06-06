
"""Manager layer — resource management."""
try:
    from arki_project.infrastructure.managers.context_manager import InfraContextManager
    from arki_project.infrastructure.managers.memory_manager import InfraMemoryManager
    from arki_project.infrastructure.managers.cache_manager import CacheManager
    from arki_project.infrastructure.managers.request_manager import RequestManager
    from arki_project.infrastructure.managers.response_manager import ResponseManager
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.managers.context_manager import InfraContextManager
        from infrastructure.managers.memory_manager import InfraMemoryManager
        from infrastructure.managers.cache_manager import CacheManager
        from infrastructure.managers.request_manager import RequestManager
        from infrastructure.managers.response_manager import ResponseManager
    except (ImportError, ModuleNotFoundError):
        InfraContextManager = None  # type: ignore
        InfraMemoryManager = None  # type: ignore
        CacheManager = None  # type: ignore
        RequestManager = None  # type: ignore
        ResponseManager = None  # type: ignore


