
"""
api_builder_pkg/endpoint_persistence.py — EndpointPersistence
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class EndpointPersistence:
    """Saves and loads custom endpoints to/from JSON file."""
    
    DEFAULT_PATH = "data/api_endpoints.json"
    
    def __init__(self, path: str = None):
        self._path = path or self.DEFAULT_PATH
    
    def save(self, endpoints: List[EndpointDefinition]) -> int:
        """Save custom (non-builtin) endpoints to JSON."""
        custom = [ep for ep in endpoints if "custom" in ep.tags or "dynamic" in ep.tags]
        
        data = []
        for ep in custom:
            data.append({
                "endpoint_id": ep.endpoint_id,
                "path": ep.path,
                "method": ep.method.value,
                "name": ep.name,
                "description": ep.description,
                "model_tier": ep.model_tier.value if hasattr(ep.model_tier, 'value') else str(ep.model_tier),
                "specific_model": ep.specific_model,
                "system_prompt": ep.system_prompt,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.param_type,
                        "description": p.description,
                        "required": p.required,
                        "default": p.default,
                        "enum": p.enum,
                    }
                    for p in ep.parameters
                ],
                "tags": ep.tags,
                "auth_level": ep.auth_level.value if hasattr(ep.auth_level, 'value') else str(ep.auth_level),
                "metadata": ep.metadata,
                "timeout_seconds": ep.timeout_seconds,
            })
        
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        with open(self._path, "w") as f:
            json.dump({"version": "2.0", "endpoints": data}, f, indent=2, ensure_ascii=False)
        
        return len(data)
    
    def load(self) -> List[Dict]:
        """Load saved endpoints from JSON."""
        if not os.path.exists(self._path):
            return []
        try:
            with open(self._path) as f:
                data = json.load(f)
            return data.get("endpoints", [])
        except (json.JSONDecodeError, KeyError):
            return []




# ═══════════════════════════════════════════════════════════════════
# API Builder Agent v4.0 TITAN
# ═══════════════════════════════════════════════════════════════════



