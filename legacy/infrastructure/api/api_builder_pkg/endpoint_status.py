
"""
api_builder_pkg/endpoint_status.py — EndpointStatus
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class EndpointStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    TESTING = "testing"
    DISABLED = "disabled"




