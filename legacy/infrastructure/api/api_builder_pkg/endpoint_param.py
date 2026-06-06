
"""
api_builder_pkg/endpoint_param.py — EndpointParam
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class EndpointParam:
    """API endpoint parameter definition."""
    name: str
    param_type: str  # "string", "number", "boolean", "array", "object"
    description: str = ""
    required: bool = True
    default: Any = None
    enum: List[str] = field(default_factory=list)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None  # regex validation




