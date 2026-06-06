
"""Proxy layer — request proxying, transformation, and forwarding."""
try:
    from arki_project.infrastructure.proxy.ai_proxy import AIProxy
    from arki_project.infrastructure.proxy.smart_proxy import SmartProxy
    from arki_project.infrastructure.proxy.reverse_proxy import ReverseProxy
    from arki_project.infrastructure.proxy.websocket_proxy import WebSocketProxy
    from arki_project.infrastructure.proxy.cloud_proxy import CloudProxy
    from arki_project.infrastructure.proxy.request_proxy import RequestProxy
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.proxy.ai_proxy import AIProxy
        from infrastructure.proxy.smart_proxy import SmartProxy
        from infrastructure.proxy.reverse_proxy import ReverseProxy
        from infrastructure.proxy.websocket_proxy import WebSocketProxy
        from infrastructure.proxy.cloud_proxy import CloudProxy
        from infrastructure.proxy.request_proxy import RequestProxy
    except (ImportError, ModuleNotFoundError):
        AIProxy = None  # type: ignore
        SmartProxy = None  # type: ignore
        ReverseProxy = None  # type: ignore
        WebSocketProxy = None  # type: ignore
        CloudProxy = None  # type: ignore
        RequestProxy = None  # type: ignore


