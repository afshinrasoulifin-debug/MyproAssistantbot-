
from __future__ import annotations
"""
AIGateway — Central gateway for all AI operations.
Single entry point: authenticate, rate-check, route, transform, respond.
"""
import asyncio, logging, time, uuid
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field



logger = logging.getLogger(__name__)

@dataclass
class GatewayRequest:
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    user_id: int = 0
    messages: List[Dict[str, str]] = field(default_factory=list)
    model: str = ""
    max_tokens: int = 65536
    temperature: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class GatewayResponse:
    request_id: str = ""
    content: str = ""
    model: str = ""
    tokens_used: int = 0
    latency: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class AIGateway:
    """Central AI gateway with middleware pipeline."""

    def __init__(self) -> None:
        self._pre_hooks: List[Callable] = []
        self._post_hooks: List[Callable] = []
        self._handler: Optional[Callable] = None
        self._request_count = 0
        self._active_requests = 0

    def set_handler(self, handler: Callable) -> None:
        self._handler = handler

    def add_pre_hook(self, hook: Callable) -> None:
        self._pre_hooks.append(hook)

    def add_post_hook(self, hook: Callable) -> None:
        self._post_hooks.append(hook)

    async def process(self, request: GatewayRequest) -> GatewayResponse:
        self._request_count += 1
        self._active_requests += 1
        t0 = time.time()

        try:
            # Pre-processing hooks
            for hook in self._pre_hooks:
                request = await hook(request) if asyncio.iscoroutinefunction(hook) else hook(request)

            # Main handler
            if not self._handler:
                return GatewayResponse(request_id=request.request_id, success=False, error="No handler")

            response = await self._handler(request)
            response.latency = time.time() - t0
            response.request_id = request.request_id

            # Post-processing hooks
            for hook in self._post_hooks:
                response = await hook(response) if asyncio.iscoroutinefunction(hook) else hook(response)

            return response
        except Exception as e:
            return GatewayResponse(
                request_id=request.request_id,
                success=False, error=str(e),
                latency=time.time() - t0
            )
        finally:
            self._active_requests -= 1

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_requests": self._request_count,
            "active_requests": self._active_requests,
        }


