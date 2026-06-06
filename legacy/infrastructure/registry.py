
from __future__ import annotations
"""
tg_bot/infrastructure/registry.py — Master Infrastructure Registry v9.8.6
═══════════════════════════════════════════════════════════════════════════
Central registry that connects ALL infrastructure components.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class InfraRegistry:
    """Master registry for all infrastructure components.

    Usage:
        registry = InfraRegistry()
        registry.auto_register()
        gateway = registry.get("ai_gateway")
    """

    _instance = None

    def __new__(cls) -> Any:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._components: Dict[str, Any] = {}
            cls._instance._initialized = False
        return cls._instance

    def register(self, name: str, component: Any) -> Any:
        self._components[name] = component
        logger.debug("Registered component: %s (%s)", name, type(component).__name__)

    def get(self, name: str) -> Any:
        return self._components.get(name)

    def has(self, name: str) -> bool:
        return name in self._components

    @property
    def component_count(self) -> int:
        return len(self._components)

    def list_components(self) -> List[str]:
        return list(self._components.keys())

    def get_by_type(self, cls_name: str) -> List[Any]:
        return [c for c in self._components.values() if type(c).__name__ == cls_name]

    def auto_register(self) -> Any:
        """Auto-discover and register ALL infrastructure components."""
        if self._initialized:
            return
        self._initialized = True

        # ── Providers (11) ──
        from arki_project.infrastructure.providers.provider_pool import ProviderPool
        from arki_project.infrastructure.providers.smart_provider import SmartProvider
        from arki_project.infrastructure.providers.fallback_provider import FallbackProvider
        from arki_project.infrastructure.providers.multi_provider import MultiProvider
        from arki_project.infrastructure.providers.dynamic_provider import DynamicProvider
        from arki_project.infrastructure.providers.auto_provider import AutoProvider
        from arki_project.infrastructure.providers.runtime_provider import RuntimeProvider
        pool = ProviderPool()
        smart = SmartProvider()
        fallback = FallbackProvider()
        self.register("provider_pool", pool)
        self.register("smart_provider", smart)
        self.register("fallback_provider", fallback)
        self.register("multi_provider", MultiProvider())
        self.register("dynamic_provider", DynamicProvider())
        self.register("auto_provider", AutoProvider())
        self.register("runtime_provider", RuntimeProvider())

        # ── Shadow + Router (need references) ──
        from arki_project.infrastructure.providers.shadow_provider import ShadowProvider
        from arki_project.infrastructure.providers.provider_router import ProviderRouter
        self.register("shadow_provider", ShadowProvider(smart, fallback))
        self.register("provider_router", ProviderRouter())

        # ── Gateway (7) ──
        from arki_project.infrastructure.gateway.ai_gateway import AIGateway
        from arki_project.infrastructure.gateway.proxy_gateway import ProxyGateway
        from arki_project.infrastructure.gateway.unified_gateway import UnifiedGateway
        from arki_project.infrastructure.gateway.smart_gateway import SmartGateway
        from arki_project.infrastructure.gateway.runtime_gateway import RuntimeGateway
        from arki_project.infrastructure.gateway.cloud_gateway import CloudGateway
        self.register("ai_gateway", AIGateway())
        self.register("proxy_gateway", ProxyGateway())
        self.register("unified_gateway", UnifiedGateway())
        self.register("smart_gateway", SmartGateway())
        self.register("runtime_gateway", RuntimeGateway())
        self.register("cloud_gateway", CloudGateway())

        # ── Clients (8) ──
        from arki_project.infrastructure.clients.unified_client import UnifiedClient
        from arki_project.infrastructure.clients.multi_client import MultiClient
        from arki_project.infrastructure.clients.smart_client import SmartClient
        self.register("unified_client", UnifiedClient())
        self.register("multi_client", MultiClient())
        self.register("smart_client", SmartClient())

        # ── Runtime (8) ──
        from arki_project.infrastructure.runtime.ai_runtime import AIRuntime
        from arki_project.infrastructure.runtime.model_runtime import ModelRuntime
        from arki_project.infrastructure.runtime.assistant_runtime import AssistantRuntime
        from arki_project.infrastructure.runtime.prompt_runtime import PromptRuntime
        from arki_project.infrastructure.runtime.context_runtime import ContextRuntime
        self.register("ai_runtime", AIRuntime())
        self.register("model_runtime", ModelRuntime())
        self.register("assistant_runtime", AssistantRuntime())
        self.register("prompt_runtime", PromptRuntime())
        self.register("context_runtime", ContextRuntime())

        # ── Engines (6) ──
        from arki_project.infrastructure.engines.inference_engine import InferenceEngine
        from arki_project.infrastructure.engines.reasoning_engine import ReasoningEngine
        from arki_project.infrastructure.engines.completion_engine import CompletionEngine
        from arki_project.infrastructure.engines.optimization_engine import OptimizationEngine
        from arki_project.infrastructure.engines.adaptive_engine import AdaptiveEngine
        self.register("inference_engine", InferenceEngine())
        self.register("reasoning_engine", ReasoningEngine())
        self.register("completion_engine", CompletionEngine())
        self.register("optimization_engine", OptimizationEngine())
        self.register("adaptive_engine", AdaptiveEngine())

        # ── Workers (6) ──
        from arki_project.infrastructure.workers.async_worker import AsyncWorker
        from arki_project.infrastructure.workers.background_worker import BackgroundWorker
        from arki_project.infrastructure.workers.queue_worker import QueueWorker
        from arki_project.infrastructure.workers.scheduler import InfraScheduler
        from arki_project.infrastructure.workers.task_runner import InfraTaskRunner
        self.register("async_worker", AsyncWorker())
        self.register("background_worker", BackgroundWorker())
        self.register("queue_worker", QueueWorker())
        self.register("scheduler", InfraScheduler())
        self.register("task_runner", InfraTaskRunner())

        # ── Wrapper / SDK / Connector ──
        from arki_project.infrastructure.wrapper.ai_wrapper import AIWrapper
        from arki_project.infrastructure.sdk.ai_sdk import AISDK
        from arki_project.infrastructure.sdk.plugin_sdk import PluginSDK
        from arki_project.infrastructure.connector.ai_connector import AIConnector
        from arki_project.infrastructure.connector.provider_connector import ProviderConnector
        from arki_project.infrastructure.connector.service_connector import ServiceConnector
        self.register("ai_wrapper", AIWrapper())
        self.register("ai_sdk", AISDK())
        self.register("plugin_sdk", PluginSDK())
        self.register("ai_connector", AIConnector())
        self.register("provider_connector", ProviderConnector())
        self.register("service_connector", ServiceConnector())

        # ── Unified API / Aggregator / Relay ──
        from arki_project.infrastructure.unified_api.ai_hub import AIHub
        from arki_project.infrastructure.aggregator.ai_aggregator import AIAggregator
        from arki_project.infrastructure.aggregator.response_aggregator import ResponseAggregator
        from arki_project.infrastructure.relay.ai_relay import AIRelay
        from arki_project.infrastructure.relay.relay_service import RelayService
        self.register("ai_hub", AIHub())
        self.register("ai_aggregator", AIAggregator())
        self.register("response_aggregator", ResponseAggregator())
        self.register("ai_relay", AIRelay())
        self.register("relay_service", RelayService())

        # ── Layers (7) ──
        from arki_project.infrastructure.layers.abstraction_layer import AbstractionLayer
        from arki_project.infrastructure.layers.compatibility_layer import CompatibilityLayer
        from arki_project.infrastructure.layers.provider_layer import ProviderLayer
        from arki_project.infrastructure.layers.integration_layer import InfraIntegrationLayer
        from arki_project.infrastructure.layers.transport_layer import InfraTransportLayer
        from arki_project.infrastructure.layers.orchestration_layer import InfraOrchestrationLayer
        self.register("abstraction_layer", AbstractionLayer("core"))
        self.register("compatibility_layer", CompatibilityLayer())
        self.register("provider_layer", ProviderLayer())
        self.register("integration_layer", InfraIntegrationLayer())
        self.register("transport_layer", InfraTransportLayer())
        self.register("orchestration_layer", InfraOrchestrationLayer())

        # ── Agents (7) ──
        from arki_project.infrastructure.agents.ai_agent import InfraAIAgent
        from arki_project.infrastructure.agents.workflow_agent import InfraWorkflowAgent
        from arki_project.infrastructure.agents.orchestration_agent import OrchestrationAgent
        from arki_project.infrastructure.agents.assistant_agent import InfraAssistantAgent
        from arki_project.infrastructure.agents.remote_agent import RemoteAgent
        self.register("ai_agent", InfraAIAgent())
        self.register("workflow_agent", InfraWorkflowAgent())
        self.register("orchestration_agent", OrchestrationAgent())
        self.register("assistant_agent", InfraAssistantAgent())
        self.register("remote_agent", RemoteAgent())

        # ── Loaders (4) ──
        from arki_project.infrastructure.loaders.runtime_loader import InfraRuntimeLoader
        from arki_project.infrastructure.loaders.plugin_loader import InfraPluginLoader
        from arki_project.infrastructure.loaders.dynamic_loader import DynamicLoader
        self.register("runtime_loader", InfraRuntimeLoader())
        self.register("plugin_loader", InfraPluginLoader())
        self.register("dynamic_loader", DynamicLoader())

        # ── Adapters (7) ──
        from arki_project.infrastructure.adapters.ai_adapter import InfraAIAdapter
        from arki_project.infrastructure.adapters.model_adapter import ModelAdapter
        from arki_project.infrastructure.adapters.provider_adapter import InfraProviderAdapter
        from arki_project.infrastructure.adapters.runtime_adapter import InfraRuntimeAdapter
        self.register("ai_adapter", InfraAIAdapter())
        self.register("model_adapter", ModelAdapter())
        self.register("provider_adapter", InfraProviderAdapter("default"))
        self.register("runtime_adapter", InfraRuntimeAdapter())

        # ── Routers (6) ──
        from arki_project.infrastructure.routers.smart_router import SmartRouter as InfraSmartRouter
        from arki_project.infrastructure.routers.model_router import InfraModelRouter
        from arki_project.infrastructure.routers.endpoint_router import EndpointRouter
        from arki_project.infrastructure.routers.request_router import RequestRouter
        from arki_project.infrastructure.routers.inference_router import InferenceRouter
        self.register("smart_router", InfraSmartRouter())
        self.register("model_router", InfraModelRouter())
        self.register("endpoint_router", EndpointRouter())
        self.register("request_router", RequestRouter())
        self.register("inference_router", InferenceRouter())

        # ── API (4) ──
        from arki_project.infrastructure.api.internal_api import InternalAPI
        from arki_project.infrastructure.api.runtime_api import RuntimeAPI
        from arki_project.infrastructure.api.transport_api import TransportAPI
        from arki_project.infrastructure.api.unified_api import UnifiedAPI
        self.register("internal_api", InternalAPI())
        self.register("runtime_api", RuntimeAPI())
        self.register("transport_api", TransportAPI())
        self.register("unified_api_v2", UnifiedAPI())

        # ── API Builder Agent (v2.4) ──
        from arki_project.infrastructure.api.api_builder import APIBuilderAgent
        self.register("api_builder", APIBuilderAgent())

        # ── Bridges (5) ──
        from arki_project.infrastructure.bridges.ai_bridge import AIBridge
        from arki_project.infrastructure.bridges.cloud_bridge import CloudBridge
        from arki_project.infrastructure.bridges.provider_bridge import InfraProviderBridge
        from arki_project.infrastructure.bridges.runtime_bridge import InfraRuntimeBridge
        from arki_project.infrastructure.bridges.websocket_bridge import InfraWebSocketBridge
        self.register("ai_bridge", AIBridge())
        self.register("cloud_bridge", CloudBridge())
        self.register("provider_bridge", InfraProviderBridge())
        self.register("runtime_bridge", InfraRuntimeBridge())
        self.register("websocket_bridge", InfraWebSocketBridge())

        # ── Bus (4) ──
        from arki_project.infrastructure.bus.command_bus import InfraCommandBus
        from arki_project.infrastructure.bus.internal_bus import InternalBus
        from arki_project.infrastructure.bus.message_bus import InfraMessageBus
        from arki_project.infrastructure.bus.service_bus import InfraServiceBus
        self.register("command_bus", InfraCommandBus())
        self.register("internal_bus", InternalBus())
        self.register("message_bus", InfraMessageBus())
        self.register("service_bus", InfraServiceBus())

        # ── Config (6) ──
        from arki_project.infrastructure.config.dynamic_config import DynamicConfig
        from arki_project.infrastructure.config.experimental_flags import ExperimentalFlags
        from arki_project.infrastructure.config.feature_flags import InfraFeatureFlags
        from arki_project.infrastructure.config.provider_config import InfraProviderConfig
        from arki_project.infrastructure.config.remote_config import InfraRemoteConfig
        from arki_project.infrastructure.config.runtime_config import InfraRuntimeConfig
        self.register("dynamic_config", DynamicConfig())
        self.register("experimental_flags", ExperimentalFlags())
        self.register("feature_flags", InfraFeatureFlags())
        self.register("provider_config", InfraProviderConfig())
        self.register("remote_config", InfraRemoteConfig())
        self.register("runtime_config", InfraRuntimeConfig())

        # ── Core (9) ──
        from arki_project.infrastructure.core.aggregator import Aggregator
        from arki_project.infrastructure.core.coordinator import OperationCoordinator
        from arki_project.infrastructure.core.executor import TaskExecutor
        from arki_project.infrastructure.core.fetcher import DataFetcher
        from arki_project.infrastructure.core.relay import Relay
        from arki_project.infrastructure.core.resolver import DependencyResolver
        from arki_project.infrastructure.core.sdk import ArkiSDK
        self.register("core_aggregator", Aggregator())
        self.register("coordinator", OperationCoordinator())
        self.register("executor", TaskExecutor())
        self.register("data_fetcher", DataFetcher())
        self.register("core_relay", Relay())
        self.register("dependency_resolver", DependencyResolver())
        self.register("arki_sdk", ArkiSDK())

        # ── Interceptors (3) ──
        from arki_project.infrastructure.interceptors.request_interceptor import InfraRequestInterceptor
        from arki_project.infrastructure.interceptors.response_interceptor import InfraResponseInterceptor
        from arki_project.infrastructure.interceptors.transport_interceptor import InfraTransportInterceptor
        self.register("request_interceptor", InfraRequestInterceptor())
        self.register("response_interceptor", InfraResponseInterceptor())
        self.register("transport_interceptor", InfraTransportInterceptor())

        # ── Managers (5) ──
        from arki_project.infrastructure.managers.cache_manager import CacheManager
        from arki_project.infrastructure.managers.context_manager import InfraContextManager
        from arki_project.infrastructure.managers.memory_manager import InfraMemoryManager
        from arki_project.infrastructure.managers.request_manager import RequestManager
        from arki_project.infrastructure.managers.response_manager import ResponseManager
        self.register("cache_manager", CacheManager())
        self.register("context_manager", InfraContextManager())
        self.register("memory_manager", InfraMemoryManager())
        self.register("request_manager", RequestManager())
        self.register("response_manager", ResponseManager())

        # ── Nodes (7) ──
        from arki_project.infrastructure.nodes.ai_node import AINode
        from arki_project.infrastructure.nodes.compute_node import ComputeNode
        from arki_project.infrastructure.nodes.edge_node import EdgeNode
        from arki_project.infrastructure.nodes.endpoint_node import EndpointNode
        from arki_project.infrastructure.nodes.provider_node import ProviderNode
        from arki_project.infrastructure.nodes.session_node import SessionNode
        from arki_project.infrastructure.nodes.worker_node import WorkerNode
        self.register("ai_node", AINode("ai_primary"))
        self.register("compute_node", ComputeNode())
        self.register("edge_node", EdgeNode())
        self.register("endpoint_node", EndpointNode())
        self.register("provider_node", ProviderNode())
        self.register("session_node", SessionNode())
        self.register("worker_node", WorkerNode())

        # ── Plugins (4) ──
        from arki_project.infrastructure.plugins.dynamic_loader import InfraDynamicLoader
        from arki_project.infrastructure.plugins.extension_system import ExtensionSystem
        from arki_project.infrastructure.plugins.module_system import ModuleSystem
        from arki_project.infrastructure.plugins.plugin_system import InfraPluginSystem
        self.register("infra_dynamic_loader", InfraDynamicLoader())
        self.register("extension_system", ExtensionSystem())
        self.register("module_system", ModuleSystem())
        self.register("infra_plugin_system", InfraPluginSystem())

        # ── Proxy (6) ──
        from arki_project.infrastructure.proxy.ai_proxy import AIProxy
        from arki_project.infrastructure.proxy.cloud_proxy import CloudProxy
        from arki_project.infrastructure.proxy.request_proxy import RequestProxy
        from arki_project.infrastructure.proxy.reverse_proxy import ReverseProxy
        from arki_project.infrastructure.proxy.smart_proxy import SmartProxy
        from arki_project.infrastructure.proxy.websocket_proxy import WebSocketProxy
        self.register("ai_proxy", AIProxy())
        self.register("cloud_proxy", CloudProxy())
        self.register("request_proxy", RequestProxy())
        self.register("reverse_proxy", ReverseProxy())
        self.register("smart_proxy", SmartProxy())
        self.register("websocket_proxy", WebSocketProxy())

        # ── Services (6) ──
        from arki_project.infrastructure.services.automation_service import InfraAutomationService
        from arki_project.infrastructure.services.integration_service import InfraIntegrationService
        from arki_project.infrastructure.services.live_service import LiveService
        from arki_project.infrastructure.services.orchestration_service import InfraOrchestrationService
        from arki_project.infrastructure.services.sync_service import InfraSyncService
        self.register("automation_service", InfraAutomationService())
        self.register("integration_service", InfraIntegrationService())
        self.register("live_service", LiveService())
        self.register("orchestration_service", InfraOrchestrationService())
        self.register("sync_service", InfraSyncService())

        # ── Sync (5) ──
        from arki_project.infrastructure.sync.context_sync import ContextSync
        from arki_project.infrastructure.sync.live_sync import InfraLiveSync
        from arki_project.infrastructure.sync.memory_sync import MemorySync
        from arki_project.infrastructure.sync.realtime_sync import InfraRealtimeSync
        from arki_project.infrastructure.sync.session_sync import SessionSync
        self.register("context_sync", ContextSync())
        self.register("live_sync", InfraLiveSync())
        self.register("memory_sync", MemorySync())
        self.register("realtime_sync", InfraRealtimeSync())
        self.register("session_sync", SessionSync())

        logger.info(
            "InfraRegistry: %d components registered across ALL %d subpackages",
            self.component_count,
            30,
        )

    def reset(self) -> Any:
        """Reset for testing."""
        self._components.clear()
        self._initialized = False


