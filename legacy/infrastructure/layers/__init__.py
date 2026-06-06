
"""Layer abstractions — architectural layer interfaces."""
try:
    from arki_project.infrastructure.layers.abstraction_layer import AbstractionLayer
    from arki_project.infrastructure.layers.compatibility_layer import CompatibilityLayer
    from arki_project.infrastructure.layers.provider_layer import ProviderLayer
    from arki_project.infrastructure.layers.integration_layer import InfraIntegrationLayer
    from arki_project.infrastructure.layers.transport_layer import InfraTransportLayer
    from arki_project.infrastructure.layers.orchestration_layer import InfraOrchestrationLayer
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.layers.abstraction_layer import AbstractionLayer
        from infrastructure.layers.compatibility_layer import CompatibilityLayer
        from infrastructure.layers.provider_layer import ProviderLayer
        from infrastructure.layers.integration_layer import InfraIntegrationLayer
        from infrastructure.layers.transport_layer import InfraTransportLayer
        from infrastructure.layers.orchestration_layer import InfraOrchestrationLayer
    except (ImportError, ModuleNotFoundError):
        AbstractionLayer = None  # type: ignore
        CompatibilityLayer = None  # type: ignore
        ProviderLayer = None  # type: ignore
        InfraIntegrationLayer = None  # type: ignore
        InfraTransportLayer = None  # type: ignore
        InfraOrchestrationLayer = None  # type: ignore


