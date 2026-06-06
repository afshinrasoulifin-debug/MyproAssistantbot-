
"""
Combined Architecture Patterns — Pairs and triples from user's specification.
Each combines multiple infrastructure components into a cohesive unit.
"""
try:
    from arki_project.infrastructure.combined.automation_layer_router import AutomationLayerRouter
    from arki_project.infrastructure.combined.ai_gateway_unified_client import AIGatewayUnifiedClient
    from arki_project.infrastructure.combined.smart_proxy_fallback import SmartProxyFallback
    from arki_project.infrastructure.combined.runtime_bridge_orchestrator import RuntimeBridgeOrchestrator
    from arki_project.infrastructure.combined.provider_pool_shadow import ProviderPoolShadow
    from arki_project.infrastructure.combined.inference_gateway_cache import InferenceGatewayCache
    from arki_project.infrastructure.combined.multi_provider_aggregator import MultiProviderAggregator
    from arki_project.infrastructure.combined.context_sync_memory import ContextSyncMemory
    from arki_project.infrastructure.combined.workflow_engine_scheduler import WorkflowEngineScheduler
    from arki_project.infrastructure.combined.plugin_system_loader import PluginSystemLoader
    from arki_project.infrastructure.combined.event_bus_dispatcher import EventBusDispatcher
    from arki_project.infrastructure.combined.smart_router_adaptive import SmartRouterAdaptive
    from arki_project.infrastructure.combined.edge_runtime_proxy import EdgeRuntimeProxy
    from arki_project.infrastructure.combined.ai_hub_connector import AIHubConnector
    from arki_project.infrastructure.combined.prompt_runtime_optimizer import PromptRuntimeOptimizer
    from arki_project.infrastructure.combined.assistant_agent_session import AssistantAgentSession
    from arki_project.infrastructure.combined.relay_transport_bridge import RelayTransportBridge
    from arki_project.infrastructure.combined.batch_worker_queue import BatchWorkerQueue
    from arki_project.infrastructure.combined.model_router_registry import ModelRouterRegistry
    from arki_project.infrastructure.combined.cloud_gateway_multi import CloudGatewayMulti
    from arki_project.infrastructure.combined.dynamic_config_flags import DynamicConfigFlags
    from arki_project.infrastructure.combined.security_interceptor_filter import SecurityInterceptorFilter
    from arki_project.infrastructure.combined.full_stack_pipeline import FullStackPipeline
    from arki_project.infrastructure.combined.mega_orchestrator import MegaOrchestrator
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.combined.automation_layer_router import AutomationLayerRouter
        from infrastructure.combined.ai_gateway_unified_client import AIGatewayUnifiedClient
        from infrastructure.combined.smart_proxy_fallback import SmartProxyFallback
        from infrastructure.combined.runtime_bridge_orchestrator import RuntimeBridgeOrchestrator
        from infrastructure.combined.provider_pool_shadow import ProviderPoolShadow
        from infrastructure.combined.inference_gateway_cache import InferenceGatewayCache
        from infrastructure.combined.multi_provider_aggregator import MultiProviderAggregator
        from infrastructure.combined.context_sync_memory import ContextSyncMemory
        from infrastructure.combined.workflow_engine_scheduler import WorkflowEngineScheduler
        from infrastructure.combined.plugin_system_loader import PluginSystemLoader
        from infrastructure.combined.event_bus_dispatcher import EventBusDispatcher
        from infrastructure.combined.smart_router_adaptive import SmartRouterAdaptive
        from infrastructure.combined.edge_runtime_proxy import EdgeRuntimeProxy
        from infrastructure.combined.ai_hub_connector import AIHubConnector
        from infrastructure.combined.prompt_runtime_optimizer import PromptRuntimeOptimizer
        from infrastructure.combined.assistant_agent_session import AssistantAgentSession
        from infrastructure.combined.relay_transport_bridge import RelayTransportBridge
        from infrastructure.combined.batch_worker_queue import BatchWorkerQueue
        from infrastructure.combined.model_router_registry import ModelRouterRegistry
        from infrastructure.combined.cloud_gateway_multi import CloudGatewayMulti
        from infrastructure.combined.dynamic_config_flags import DynamicConfigFlags
        from infrastructure.combined.security_interceptor_filter import SecurityInterceptorFilter
        from infrastructure.combined.full_stack_pipeline import FullStackPipeline
        from infrastructure.combined.mega_orchestrator import MegaOrchestrator
    except (ImportError, ModuleNotFoundError):
        AutomationLayerRouter = None  # type: ignore
        AIGatewayUnifiedClient = None  # type: ignore
        SmartProxyFallback = None  # type: ignore
        RuntimeBridgeOrchestrator = None  # type: ignore
        ProviderPoolShadow = None  # type: ignore
        InferenceGatewayCache = None  # type: ignore
        MultiProviderAggregator = None  # type: ignore
        ContextSyncMemory = None  # type: ignore
        WorkflowEngineScheduler = None  # type: ignore
        PluginSystemLoader = None  # type: ignore
        EventBusDispatcher = None  # type: ignore
        SmartRouterAdaptive = None  # type: ignore
        EdgeRuntimeProxy = None  # type: ignore
        AIHubConnector = None  # type: ignore
        PromptRuntimeOptimizer = None  # type: ignore
        AssistantAgentSession = None  # type: ignore
        RelayTransportBridge = None  # type: ignore
        BatchWorkerQueue = None  # type: ignore
        ModelRouterRegistry = None  # type: ignore
        CloudGatewayMulti = None  # type: ignore
        DynamicConfigFlags = None  # type: ignore
        SecurityInterceptorFilter = None  # type: ignore
        FullStackPipeline = None  # type: ignore
        MegaOrchestrator = None  # type: ignore


