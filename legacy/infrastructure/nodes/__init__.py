
"""Node layer — distributed compute nodes."""
try:
    from arki_project.infrastructure.nodes.ai_node import AINode
    from arki_project.infrastructure.nodes.worker_node import WorkerNode
    from arki_project.infrastructure.nodes.edge_node import EdgeNode
    from arki_project.infrastructure.nodes.compute_node import ComputeNode
    from arki_project.infrastructure.nodes.endpoint_node import EndpointNode
    from arki_project.infrastructure.nodes.provider_node import ProviderNode
    from arki_project.infrastructure.nodes.session_node import SessionNode
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.nodes.ai_node import AINode
        from infrastructure.nodes.worker_node import WorkerNode
        from infrastructure.nodes.edge_node import EdgeNode
        from infrastructure.nodes.compute_node import ComputeNode
        from infrastructure.nodes.endpoint_node import EndpointNode
        from infrastructure.nodes.provider_node import ProviderNode
        from infrastructure.nodes.session_node import SessionNode
    except (ImportError, ModuleNotFoundError):
        AINode = None  # type: ignore
        WorkerNode = None  # type: ignore
        EdgeNode = None  # type: ignore
        ComputeNode = None  # type: ignore
        EndpointNode = None  # type: ignore
        ProviderNode = None  # type: ignore
        SessionNode = None  # type: ignore


