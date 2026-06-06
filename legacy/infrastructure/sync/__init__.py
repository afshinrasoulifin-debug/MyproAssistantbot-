
"""Sync layer — data synchronization across components."""
try:
    from arki_project.infrastructure.sync.context_sync import ContextSync
    from arki_project.infrastructure.sync.memory_sync import MemorySync
    from arki_project.infrastructure.sync.session_sync import SessionSync
    from arki_project.infrastructure.sync.live_sync import InfraLiveSync
    from arki_project.infrastructure.sync.realtime_sync import InfraRealtimeSync
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.sync.context_sync import ContextSync
        from infrastructure.sync.memory_sync import MemorySync
        from infrastructure.sync.session_sync import SessionSync
        from infrastructure.sync.live_sync import InfraLiveSync
        from infrastructure.sync.realtime_sync import InfraRealtimeSync
    except (ImportError, ModuleNotFoundError):
        ContextSync = None  # type: ignore
        MemorySync = None  # type: ignore
        SessionSync = None  # type: ignore
        InfraLiveSync = None  # type: ignore
        InfraRealtimeSync = None  # type: ignore


