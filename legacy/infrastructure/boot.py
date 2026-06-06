
from __future__ import annotations
"""
infrastructure/boot.py — Boot the entire infrastructure layer v9.8.6
Called from main.py during startup.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Global reference for other modules to access
_infra_context = None

def get_infra() -> Any:
    """Get the booted infrastructure context (singleton)."""
    return _infra_context


async def boot_infrastructure() -> Any:
    """Initialize all infrastructure components and wire them together."""
    global _infra_context

    from arki_project.infrastructure.registry import InfraRegistry

    # ── Combined Patterns ──
    from arki_project.infrastructure.combined.mega_orchestrator import MegaOrchestrator
    from arki_project.infrastructure.combined.full_stack_pipeline import FullStackPipeline
    from arki_project.infrastructure.combined.event_bus_dispatcher import EventBusDispatcher
    from arki_project.infrastructure.combined.dynamic_config_flags import DynamicConfigFlags
    from arki_project.infrastructure.combined.context_sync_memory import ContextSyncMemory
    from arki_project.infrastructure.combined.ai_gateway_unified_client import AIGatewayUnifiedClient
    from arki_project.infrastructure.combined.smart_proxy_fallback import SmartProxyFallback
    from arki_project.infrastructure.combined.runtime_bridge_orchestrator import RuntimeBridgeOrchestrator
    from arki_project.infrastructure.combined.provider_pool_shadow import ProviderPoolShadow
    from arki_project.infrastructure.combined.inference_gateway_cache import InferenceGatewayCache
    from arki_project.infrastructure.combined.multi_provider_aggregator import MultiProviderAggregator
    from arki_project.infrastructure.combined.workflow_engine_scheduler import WorkflowEngineScheduler
    from arki_project.infrastructure.combined.plugin_system_loader import PluginSystemLoader
    from arki_project.infrastructure.combined.smart_router_adaptive import SmartRouterAdaptive
    from arki_project.infrastructure.combined.edge_runtime_proxy import EdgeRuntimeProxy
    from arki_project.infrastructure.combined.ai_hub_connector import AIHubConnector
    from arki_project.infrastructure.combined.prompt_runtime_optimizer import PromptRuntimeOptimizer
    from arki_project.infrastructure.combined.assistant_agent_session import AssistantAgentSession
    from arki_project.infrastructure.combined.relay_transport_bridge import RelayTransportBridge
    from arki_project.infrastructure.combined.batch_worker_queue import BatchWorkerQueue
    from arki_project.infrastructure.combined.model_router_registry import ModelRouterRegistry
    from arki_project.infrastructure.combined.cloud_gateway_multi import CloudGatewayMulti
    from arki_project.infrastructure.combined.security_interceptor_filter import SecurityInterceptorFilter
    from arki_project.infrastructure.combined.automation_layer_router import AutomationLayerRouter

    # ── 1. Create & populate registry ──
    registry = InfraRegistry()
    registry.reset()  # Fresh start
    registry.auto_register()

    # ── 2. Create combined patterns ──
    event_bus = EventBusDispatcher()
    config = DynamicConfigFlags()
    pipeline = FullStackPipeline()
    context_memory = ContextSyncMemory()
    gateway_client = AIGatewayUnifiedClient()
    smart_proxy = SmartProxyFallback()
    runtime_bridge = RuntimeBridgeOrchestrator()
    pool_shadow = ProviderPoolShadow()
    inference_cache = InferenceGatewayCache()
    multi_agg = MultiProviderAggregator()
    workflow_sched = WorkflowEngineScheduler()
    plugin_loader = PluginSystemLoader()
    smart_router = SmartRouterAdaptive()
    edge_proxy = EdgeRuntimeProxy()
    hub_connector = AIHubConnector()
    prompt_opt = PromptRuntimeOptimizer()
    agent_session = AssistantAgentSession()
    relay_bridge = RelayTransportBridge()
    batch_queue = BatchWorkerQueue()
    model_router = ModelRouterRegistry()
    cloud_multi = CloudGatewayMulti()
    security_filter = SecurityInterceptorFilter()
    auto_router = AutomationLayerRouter()

    # ── 3. Production_Strict Profile (v17.3: APEX TERMINATED) ──
    config.set("production_strict", True)
    config.set("max_tokens", 65536)
    config.set("rate_limit", True)         # v17.3: Rate limiting ENFORCED
    config.set("all_models_available", True)
    config.set("safety_filter", True)      # v17.3: Safety filter ENFORCED
    config.set("budget_check", True)       # v17.3: Budget checks ENFORCED
    config.set("plan_enforcement", True)   # v17.3: Plan enforcement ENFORCED
    config.enable_flag("unlimited_tokens")
    config.enable_flag("all_providers")
    config.enable_flag("production_strict")

    # ── 4. Register combined patterns ──
    combined_registry = {
        "event_bus": event_bus,
        "config_flags": config,
        "pipeline": pipeline,
        "context_memory": context_memory,
        "gateway_client": gateway_client,
        "smart_proxy": smart_proxy,
        "runtime_bridge": runtime_bridge,
        "pool_shadow": pool_shadow,
        "inference_cache": inference_cache,
        "multi_aggregator": multi_agg,
        "workflow_scheduler": workflow_sched,
        "plugin_loader": plugin_loader,
        "smart_router_adaptive": smart_router,
        "edge_proxy": edge_proxy,
        "hub_connector": hub_connector,
        "prompt_optimizer": prompt_opt,
        "agent_session": agent_session,
        "relay_bridge": relay_bridge,
        "batch_queue": batch_queue,
        "model_router_registry": model_router,
        "cloud_multi": cloud_multi,
        "security_filter": security_filter,
        "automation_router": auto_router,
    }
    for name, component in combined_registry.items():
        registry.register(f"combined.{name}", component)

    # ── 5. Boot orchestrator ──
    orchestrator = MegaOrchestrator()
    orchestrator.set_registry(registry)
    orchestrator.set_pipeline(pipeline)
    orchestrator.set_event_bus(event_bus)
    await orchestrator.boot()
    registry.register("orchestrator", orchestrator)

    # ── 6. Emit boot event ──
    await event_bus.emit("infrastructure.booted", {
        "component_count": registry.component_count,
        "combined_patterns": len(combined_registry),
    })

    _infra_context = {
        "registry": registry,
        "orchestrator": orchestrator,
        "pipeline": pipeline,
        "event_bus": event_bus,
        "config": config,
        "context_memory": context_memory,
        "gateway_client": gateway_client,
        "combined": combined_registry,
    }

    logger.info(
        "🚀 Infrastructure v9.8.6 booted: %d components + %d combined patterns",
        registry.component_count,
        len(combined_registry),
    )
    return _infra_context


