
from __future__ import annotations
"""
architecture.service.remote — RemoteService
════════════════════════════════════════════
Remote service integration and API client management.
Covers: remote-service, remote-adapter, remote-helper, remote-config
"""
import logging, time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional



logger = logging.getLogger(__name__)

@dataclass
class ServiceEndpoint:
    name: str
    url: str
    api_key: Optional[str] = None
    timeout_s: float = 30.0
    healthy: bool = True
    last_check: float = 0
    request_count: int = 0
    error_count: int = 0

class RemoteService:
    """Manage connections to remote APIs and services."""
    def __init__(self) -> None:
        self._endpoints: Dict[str, ServiceEndpoint] = {}

    def register(self, name: str, url: str, api_key: Optional[str] = None,
                 timeout_s: float = 30.0) -> ServiceEndpoint:
        ep = ServiceEndpoint(name=name, url=url, api_key=api_key, timeout_s=timeout_s)
        self._endpoints[name] = ep
        return ep

    def get(self, name: str) -> Optional[ServiceEndpoint]:
        return self._endpoints.get(name)

    def mark_healthy(self, name: str, healthy: bool) -> None:
        ep = self._endpoints.get(name)
        if ep:
            ep.healthy = healthy
            ep.last_check = time.time()

    def healthy_endpoints(self) -> List[ServiceEndpoint]:
        return [ep for ep in self._endpoints.values() if ep.healthy]

    @property
    def stats(self) -> Dict[str, Any]:
        return {name: {"healthy": ep.healthy, "requests": ep.request_count, "errors": ep.error_count}
                for name, ep in self._endpoints.items()}


