
"""Interceptor layer — request/response interception."""
try:
    from arki_project.infrastructure.interceptors.request_interceptor import InfraRequestInterceptor
    from arki_project.infrastructure.interceptors.response_interceptor import InfraResponseInterceptor
    from arki_project.infrastructure.interceptors.transport_interceptor import InfraTransportInterceptor
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.interceptors.request_interceptor import InfraRequestInterceptor
        from infrastructure.interceptors.response_interceptor import InfraResponseInterceptor
        from infrastructure.interceptors.transport_interceptor import InfraTransportInterceptor
    except (ImportError, ModuleNotFoundError):
        InfraRequestInterceptor = None  # type: ignore
        InfraResponseInterceptor = None  # type: ignore
        InfraTransportInterceptor = None  # type: ignore


