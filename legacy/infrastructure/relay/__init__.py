
"""Relay layer — message relaying between components."""
try:
    from arki_project.infrastructure.relay.ai_relay import AIRelay
    from arki_project.infrastructure.relay.relay_service import RelayService
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.relay.ai_relay import AIRelay
        from infrastructure.relay.relay_service import RelayService
    except (ImportError, ModuleNotFoundError):
        AIRelay = None  # type: ignore
        RelayService = None  # type: ignore


