
from __future__ import annotations
"""
extra/infra_connector.py — APEX ↔ Infrastructure Full Bridge v2.0
═════════════════════════════════════════════════════════════════════
Bidirectional connector between APEX multi-model engine and
the full infrastructure layer, including the API Builder Agent.

Architecture
────────────
  APEX (TS)                  Infrastructure (Python)
  ┌───────────┐                 ┌───────────────────────┐
  │ Express   │  ←── HTTP ──→   │ InfraRegistry (100+)  │
  │ Agent     │                 │ APIBuilderAgent       │
  │ 20 tools  │                 │ ModelRouter (72)      │
  │ OpenAPI   │  ←── Events →   │ AIGateway             │
  │ Models    │                 │ SmartClient           │
  └───────────┘                 │ AgentExecutor (20)    │
       │                        └───────────────────────┘
       │                                   │
       └──── Bridge (httpx) ──────────────┘

New in v2.0
───────────
  • API Builder integration — create/list/test endpoints
  • Model routing — SmartClient ↔ APEX model pool
  • Agent execution bridge — Python ↔ TS agent forwarding
  • Infrastructure health aggregation
  • OpenAPI spec forwarding
  • Endpoint stats collection
"""


import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class ApexInfraConnector:
    """Bidirectional bridge between APEX and infrastructure components.

    Provides access to:
      • InfraRegistry (100+ components)
      • APIBuilderAgent (endpoint creation, model routing, testing)
      • AIGateway (request processing pipeline)
      • SmartClient (auto-model selection)
      • AgentExecutor (20 tools including 8 API/infra tools)
      • EventBus (cross-layer event propagation)
    """

    _instance = None

    def __new__(cls) -> Any:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connected = False
            cls._instance._registry = None
            cls._instance._event_bus = None
            cls._instance._config = None
            cls._instance._api_builder = None
            cls._instance._model_router = None
            cls._instance._hooks: Dict[str, List[Callable]] = {}
            cls._instance._stats = {
                "requests": 0,
                "api_calls": 0,
                "agent_calls": 0,
                "model_routes": 0,
                "errors": 0,
                "connected_since": None,
            }
        return cls._instance

    # ── Connection ──────────────────────────────────────────────

    def connect(self) -> bool:
        """Establish bidirectional connection to infrastructure."""
        try:
            from arki_project.core.boot import get_infra
            infra = get_infra()
            if infra:
                self._registry = infra["registry"]
                self._event_bus = infra.get("event_bus")
                self._config = infra.get("config")
                self._connected = True
                self._stats["connected_since"] = time.time()

                # Initialize API Builder
                self._init_api_builder()

                logger.info(
                    "APEX ↔ Infrastructure FULL BRIDGE connected (%d components, API Builder: %s)",
                    self._registry.component_count,
                    "active" if self._api_builder else "pending",
                )
                return True
        except ImportError:
            # Infrastructure not available — connect API builder standalone
            self._init_api_builder()
            if self._api_builder:
                self._connected = True
                self._stats["connected_since"] = time.time()
                logger.info("APEX ↔ API Builder connected (standalone mode, 72 models)")
                return True
            logger.debug("Infrastructure not available for APEX")
        return False

    def _init_api_builder(self) -> Any:
        """Initialize the API Builder agent."""
        try:
            from infrastructure.api.api_builder import get_api_builder
            self._api_builder = get_api_builder()
            self._model_router = self._api_builder.router
            logger.info("API Builder connected — 72 models, %d endpoints",
                        self._api_builder.registry.count)
        except ImportError:
            logger.debug("API Builder not available")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Infrastructure Access ───────────────────────────────────

    def get_provider(self, name: str) -> Any:
        """Get infrastructure provider by name."""
        if self._registry:
            return self._registry.get(name)
        return None

    def get_gateway(self) -> Any:
        """Get the AI gateway."""
        return self.get_provider("ai_gateway")

    def get_smart_client(self) -> Any:
        """Get the SmartClient for model auto-selection."""
        return self.get_provider("smart_client")

    def get_all_providers(self) -> Dict[str, Any]:
        """Get all registered providers."""
        if self._registry:
            return {k: self._registry.get(k) for k in self._registry.list_components()
                    if "provider" in k}
        return {}

    def get_all_components(self) -> List[str]:
        """List all infrastructure components."""
        if self._registry:
            return self._registry.list_components()
        return []

    # ── API Builder Access ──────────────────────────────────────

    @property
    def api_builder(self) -> Any:
        """Get the API Builder agent."""
        return self._api_builder

    @property
    def model_router(self) -> Any:
        """Get the Model Router (72 models)."""
        return self._model_router

    async def create_endpoint(self, path: str, name: str, description: str,
                              system_prompt: str = "", model_tier: str = "auto",
                              **kwargs) -> Dict[str, Any]:
        """Create a new dynamic API endpoint via the builder."""
        self._stats["api_calls"] += 1
        if not self._api_builder:
            return {"error": "API Builder not initialized"}

        if not self._api_builder._initialized:
            await self._api_builder.initialize()

        ep = self._api_builder.create_endpoint(
            path=path, name=name, description=description,
            system_prompt=system_prompt, model_tier=model_tier,
            **kwargs,
        )
        return {
            "endpoint_id": ep.endpoint_id,
            "path": ep.path,
            "method": ep.method.value,
            "model_tier": ep.model_tier.value,
            "status": ep.status.value,
        }

    async def execute_endpoint(self, endpoint_id: str, data: Dict) -> Dict[str, Any]:
        """Execute a registered endpoint."""
        self._stats["api_calls"] += 1
        if not self._api_builder:
            return {"error": "API Builder not initialized"}

        if not self._api_builder._initialized:
            await self._api_builder.initialize()

        return await self._api_builder.execute_endpoint(endpoint_id, data)

    def list_endpoints(self) -> List[Dict[str, Any]]:
        """List all API endpoints."""
        if not self._api_builder:
            return []
        return [
            {
                "id": ep.endpoint_id,
                "method": ep.method.value,
                "path": f"/{ep.version}/{ep.path}",
                "name": ep.name,
                "model_tier": ep.model_tier.value,
                "status": ep.status.value,
            }
            for ep in self._api_builder.registry.list_all()
        ]

    def get_openapi_spec(self) -> Dict[str, Any]:
        """Generate OpenAPI 3.1 spec for all endpoints."""
        if not self._api_builder:
            return {"error": "API Builder not initialized"}
        return self._api_builder.get_openapi_spec()

    # ── Model Routing ───────────────────────────────────────────

    def route_model(self, task_type: str = "general",
                    tier: str = "auto") -> str:
        """Route to optimal model for a task."""
        self._stats["model_routes"] += 1
        if self._model_router:
            from infrastructure.api.api_builder import ModelTier
            tier_map = {
                "auto": ModelTier.AUTO, "fast": ModelTier.FAST,
                "pro": ModelTier.PRO, "ultra": ModelTier.ULTRA,
                "consortium": ModelTier.CONSORTIUM,
            }
            return self._model_router.select_model(
                tier_map.get(tier, ModelTier.AUTO),
                task_type=task_type,
            )
        # Fallback routing
        fallback = {
            "code": "g-claude-opus-4", "analysis": "gemini-pro",
            "creative": "g-gpt5", "fast": "gemini-flash",
            "math": "g-deepseek-r1",
        }
        return fallback.get(task_type, "gemini-pro")

    def list_models(self, tier: Optional[str] = None) -> List[Dict[str, str]]:
        """List all 72 models, optionally filtered by tier."""
        if self._api_builder:
            models = self._api_builder.get_all_model_keys()
            if tier:
                models = [m for m in models if m.get("tier") == tier]
            return models
        return []

    # ── Agent Execution Bridge ──────────────────────────────────

    async def execute_agent(self, query: str, model: Optional[str] = None,
                            max_steps: int = 50, tools: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute agent task via the Python agent executor.

        Routes through infrastructure for full tool access including
        the 8 new API/infra tools.
        """
        self._stats["agent_calls"] += 1
        try:
            from utils.agent_executor import get_default_agent
            agent = get_default_agent()
            trace = await agent.execute(
                query=query,
                model=model or self.route_model("general"),
                max_steps=max_steps,
                tools=tools,
            )
            return {
                "success": trace.status == "completed",
                "answer": trace.final_answer,
                "steps": len(trace.steps),
                "tokens_used": trace.tokens_used,
                "duration_ms": trace.total_duration_ms,
                "model": trace.model,
                "tools_used": [s.tool_name for s in trace.steps if s.tool_name],
            }
        except Exception as e:
            self._stats["errors"] += 1
            return {"success": False, "error": str(e)}

    # ── Events ──────────────────────────────────────────────────

    async def emit_event(self, event: str, data: Any = None) -> None:
        """Emit event through infrastructure bus."""
        if self._event_bus:
            await self._event_bus.emit(f"apex.{event}", data)
        # Also trigger local hooks
        for hook in self._hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(data)
                else:
                    hook(data)
            except Exception as e:
                logger.warning("Hook error for %s: %s", event, e)

    def on_event(self, event: str, hook: Callable) -> None:
        """Register a hook for an event."""
        self._hooks.setdefault(event, []).append(hook)

    # ── Config ──────────────────────────────────────────────────

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get infrastructure config value."""
        if self._config:
            return self._config.get(key, default)
        return default

    # ── Health & Status ─────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        """Full health check of the bridge."""
        components = {
            "connector": self._connected,
            "registry": self._registry is not None,
            "api_builder": self._api_builder is not None,
            "model_router": self._model_router is not None,
            "event_bus": self._event_bus is not None,
        }

        if self._registry:
            for name in ["ai_gateway", "smart_client", "unified_client"]:
                components[name] = self._registry.has(name)

        return {
            "status": "healthy" if all(v for k, v in components.items()
                                       if k in ("connector", "api_builder")) else "degraded",
            "mode": "full" if self._registry else "standalone",
            "components": components,
            "models": 72,
            "endpoints": self._api_builder.registry.count if self._api_builder else 0,
            "stats": self._stats,
        }

    def status(self) -> Dict[str, Any]:
        """Full bridge status."""
        return {
            "version": "2.0.0-TITANIUM",
            "connected": self._connected,
            "mode": "full" if self._registry else ("standalone" if self._api_builder else "disconnected"),
            "infrastructure_components": len(self.get_all_components()),
            "api_endpoints": self._api_builder.registry.count if self._api_builder else 0,
            "models": 72,
            "agent_tools": 20,
            "stats": self._stats,
            "capabilities": [
                "endpoint_creation",
                "model_routing",
                "agent_execution",
                "openapi_generation",
                "health_monitoring",
                "event_propagation",
            ],
        }


def get_apex_connector() -> ApexInfraConnector:
    """Get singleton connector."""
    conn = ApexInfraConnector()
    if not conn.is_connected:
        conn.connect()
    return conn


# Alias for external callers that expect InfraConnector
InfraConnector = ApexInfraConnector
get_infra_connector = get_apex_connector


