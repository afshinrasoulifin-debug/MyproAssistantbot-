
"""Router layer — intelligent request routing."""
try:
    from arki_project.infrastructure.routers.smart_router import SmartRouter
    from arki_project.infrastructure.routers.model_router import InfraModelRouter
    from arki_project.infrastructure.routers.endpoint_router import EndpointRouter
    from arki_project.infrastructure.routers.request_router import RequestRouter
    from arki_project.infrastructure.routers.inference_router import InferenceRouter
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.routers.smart_router import SmartRouter
        from infrastructure.routers.model_router import InfraModelRouter
        from infrastructure.routers.endpoint_router import EndpointRouter
        from infrastructure.routers.request_router import RequestRouter
        from infrastructure.routers.inference_router import InferenceRouter
    except (ImportError, ModuleNotFoundError):
        SmartRouter = None  # type: ignore
        InfraModelRouter = None  # type: ignore
        EndpointRouter = None  # type: ignore
        RequestRouter = None  # type: ignore
        InferenceRouter = None  # type: ignore


