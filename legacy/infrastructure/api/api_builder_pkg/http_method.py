
"""
api_builder_pkg/http_method.py — HttpMethod
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"




