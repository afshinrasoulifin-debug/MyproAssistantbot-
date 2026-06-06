
"""
api_builder_pkg/endpoint_registry.py — EndpointRegistry
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class EndpointRegistry:
    """Registry of all dynamically created API endpoints."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._endpoints: Dict[str, EndpointDefinition] = {}
            cls._instance._stats: Dict[str, Dict] = defaultdict(
                lambda: {"calls": 0, "errors": 0, "total_latency": 0.0, "total_tokens": 0}
            )
        return cls._instance

    def register(self, endpoint: EndpointDefinition) -> str:
        """Register a new endpoint. Returns endpoint_id."""
        key = f"{endpoint.method.value}:{endpoint.version}/{endpoint.path}"
        self._endpoints[endpoint.endpoint_id] = endpoint
        logger.info("Registered endpoint: %s %s/%s [%s]",
                     endpoint.method.value, endpoint.version, endpoint.path, endpoint.endpoint_id)
        return endpoint.endpoint_id

    def get(self, endpoint_id: str) -> Optional[EndpointDefinition]:
        return self._endpoints.get(endpoint_id)

    def find_by_path(self, path: str, method: HttpMethod = HttpMethod.POST) -> Optional[EndpointDefinition]:
        for ep in self._endpoints.values():
            if ep.path == path and ep.method == method and ep.status == EndpointStatus.ACTIVE:
                return ep
        return None

    def list_all(self) -> List[EndpointDefinition]:
        return list(self._endpoints.values())

    def list_active(self) -> List[EndpointDefinition]:
        return [ep for ep in self._endpoints.values() if ep.status == EndpointStatus.ACTIVE]

    def deprecate(self, endpoint_id: str) -> bool:
        ep = self._endpoints.get(endpoint_id)
        if ep:
            ep.status = EndpointStatus.DEPRECATED
            return True
        return False

    def delete(self, endpoint_id: str) -> bool:
        return self._endpoints.pop(endpoint_id, None) is not None

    def record_call(self, endpoint_id: str, latency_ms: float, tokens: int, error: bool = False):
        stats = self._stats[endpoint_id]
        stats["calls"] += 1
        stats["total_latency"] += latency_ms
        stats["total_tokens"] += tokens
        if error:
            stats["errors"] += 1

    def get_stats(self, endpoint_id: str) -> Dict:
        stats = self._stats[endpoint_id]
        calls = stats["calls"] or 1
        return {
            "total_calls": stats["calls"],
            "error_count": stats["errors"],
            "total_latency": stats["total_latency"],
            "total_tokens": stats["total_tokens"],
            "avg_latency_ms": stats["total_latency"] / calls,
            "error_rate": stats["errors"] / calls,
        }

    def get_all_stats(self) -> Dict[str, Dict]:
        return {eid: self.get_stats(eid) for eid in self._endpoints}

    @property
    def count(self) -> int:
        return len(self._endpoints)

    @property
    def active_count(self) -> int:
        return sum(1 for ep in self._endpoints.values() if ep.status == EndpointStatus.ACTIVE)


# ═══════════════════════════════════════════════════════════════════
# Model Router — connects to all 79 models
# ═══════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════
# Model Router — Dynamic from models_registry
# ═══════════════════════════════════════════════════════════════════



