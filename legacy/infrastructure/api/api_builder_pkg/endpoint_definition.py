
"""
api_builder_pkg/endpoint_definition.py — EndpointDefinition
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class EndpointDefinition:
    """Full API endpoint definition."""
    endpoint_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    path: str = ""
    method: HttpMethod = HttpMethod.POST
    name: str = ""
    description: str = ""
    version: str = "v1"
    auth_level: AuthLevel = AuthLevel.BASIC
    model_tier: ModelTier = ModelTier.AUTO
    specific_model: Optional[str] = None  # Override auto-selection
    parameters: List[EndpointParam] = field(default_factory=list)
    system_prompt: str = ""  # System prompt for AI endpoints
    response_schema: Dict[str, Any] = field(default_factory=dict)
    rate_limit_per_minute: int = 60
    max_tokens: int = 65536
    temperature: float = 0.7
    timeout_seconds: float = 120.0
    tags: List[str] = field(default_factory=list)
    status: EndpointStatus = EndpointStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)




