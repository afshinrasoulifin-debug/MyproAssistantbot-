
"""
api_builder_pkg/auth_level.py — AuthLevel
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class AuthLevel(str, Enum):
    NONE = "none"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"




