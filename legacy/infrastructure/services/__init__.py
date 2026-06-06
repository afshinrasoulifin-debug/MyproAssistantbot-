
"""Service layer — high-level services."""
try:
    from arki_project.infrastructure.services.relay_service import RelayService
    from arki_project.infrastructure.services.integration_service import InfraIntegrationService
    from arki_project.infrastructure.services.orchestration_service import InfraOrchestrationService
    from arki_project.infrastructure.services.automation_service import InfraAutomationService
    from arki_project.infrastructure.services.sync_service import InfraSyncService
    from arki_project.infrastructure.services.live_service import LiveService
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.services.relay_service import RelayService
        from infrastructure.services.integration_service import InfraIntegrationService
        from infrastructure.services.orchestration_service import InfraOrchestrationService
        from infrastructure.services.automation_service import InfraAutomationService
        from infrastructure.services.sync_service import InfraSyncService
        from infrastructure.services.live_service import LiveService
    except (ImportError, ModuleNotFoundError):
        RelayService = None  # type: ignore
        InfraIntegrationService = None  # type: ignore
        InfraOrchestrationService = None  # type: ignore
        InfraAutomationService = None  # type: ignore
        InfraSyncService = None  # type: ignore
        LiveService = None  # type: ignore


