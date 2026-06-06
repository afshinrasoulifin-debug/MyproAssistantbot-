
"""
free_access_router_pkg/free_call_result.py — FreeCallResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
@dataclass
class FreeCallResult:
    """Result from a free access call with transparency metadata."""
    text: str
    actual_model_key: str = ""
    actual_model_name: str = ""
    actual_model_id: str = ""
    requested_model_key: str = ""
    was_fallback: bool = False
    route_method: str = ""

    @property
    def transparency_label(self) -> str:
        """Persian label showing what model actually responded."""
        if not self.was_fallback:
            return ""
        return f"⚡ پاسخ واقعی از: {self.actual_model_name}"




