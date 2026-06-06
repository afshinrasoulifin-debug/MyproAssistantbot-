
"""Core infrastructure utilities."""
try:
    from arki_project.infrastructure.core.wrapper import AIWrapper
    from arki_project.infrastructure.core.sdk import ArkiSDK
    from arki_project.infrastructure.core.connector import Connector
    from arki_project.infrastructure.core.helper import InfraHelper
    from arki_project.infrastructure.core.relay import Relay
    from arki_project.infrastructure.core.fetcher import DataFetcher
    from arki_project.infrastructure.core.resolver import DependencyResolver
    from arki_project.infrastructure.core.coordinator import OperationCoordinator
    from arki_project.infrastructure.core.executor import TaskExecutor
    from arki_project.infrastructure.core.aggregator import Aggregator
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.core.wrapper import AIWrapper
        from infrastructure.core.sdk import ArkiSDK
        from infrastructure.core.connector import Connector
        from infrastructure.core.helper import InfraHelper
        from infrastructure.core.relay import Relay
        from infrastructure.core.fetcher import DataFetcher
        from infrastructure.core.resolver import DependencyResolver
        from infrastructure.core.coordinator import OperationCoordinator
        from infrastructure.core.executor import TaskExecutor
        from infrastructure.core.aggregator import Aggregator
    except (ImportError, ModuleNotFoundError):
        AIWrapper = None  # type: ignore
        ArkiSDK = None  # type: ignore
        Connector = None  # type: ignore
        InfraHelper = None  # type: ignore
        Relay = None  # type: ignore
        DataFetcher = None  # type: ignore
        DependencyResolver = None  # type: ignore
        OperationCoordinator = None  # type: ignore
        TaskExecutor = None  # type: ignore
        Aggregator = None  # type: ignore


