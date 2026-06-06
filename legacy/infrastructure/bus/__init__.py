
"""Bus layer — message passing infrastructure."""
try:
    from arki_project.infrastructure.bus.internal_bus import InternalBus
    from arki_project.infrastructure.bus.message_bus import InfraMessageBus
    from arki_project.infrastructure.bus.command_bus import InfraCommandBus
    from arki_project.infrastructure.bus.service_bus import InfraServiceBus
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.bus.internal_bus import InternalBus
        from infrastructure.bus.message_bus import InfraMessageBus
        from infrastructure.bus.command_bus import InfraCommandBus
        from infrastructure.bus.service_bus import InfraServiceBus
    except (ImportError, ModuleNotFoundError):
        InternalBus = None  # type: ignore
        InfraMessageBus = None  # type: ignore
        InfraCommandBus = None  # type: ignore
        InfraServiceBus = None  # type: ignore


