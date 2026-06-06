
"""
agent_executor_pkg/tool_category.py — ToolCategory
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ToolCategory(str, Enum):
    SEARCH      = "search"
    RECON       = "recon"
    AUTOMATION  = "automation"
    CODE        = "code"
    DATA        = "data"
    CRYPTO      = "crypto"
    NETWORK     = "network"
    ANALYSIS    = "analysis"
    UTILITY     = "utility"
    MEMORY      = "memory"
    MULTIMODAL  = "multimodal"
    API         = "api"
    MODELS      = "models"
    INFRA       = "infrastructure"




