
from __future__ import annotations
"""
architecture.setup — Wire all architecture components into the bot
══════════════════════════════════════════════════════════════════
Call `init_architecture()` from main.py during startup.
"""


import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def init_architecture() -> Dict[str, Any]:
    """
    Initialize ALL architecture components and return the registry.
    Called once at bot startup from main.py.
    """
    registry: Dict[str, Any] = {}

    # ── Layer 1: Core ──
    from .core import get_runtime, get_bootstrapper, get_config, get_hooks, get_hot_reload
    runtime = get_runtime()
    bootstrapper = get_bootstrapper()
    config = get_config()
    hooks = get_hooks()
    hot_reload = get_hot_reload()
    registry.update({
        "runtime_core": runtime,
        "bootstrapper": bootstrapper,
        "config": config,
        "hooks": hooks,
        "hot_reload": hot_reload,
    })

    # ── Layer 2: Engines ──
    from .engine.workflow import WorkflowEngine as ArchWorkflowEngine
    from .engine.automation import AutomationEngine
    from .engine.orchestration import OrchestrationEngine
    from .engine.execution import ExecutionEngine, ProcessingEngine
    from .engine.template import TemplateEngine
    from .engine.smart import SmartEngine, AdaptiveEngine, PerformanceEngine, ActionEngine

    registry.update({
        "workflow_engine": ArchWorkflowEngine(),
        "automation_engine": AutomationEngine(),
        "orchestration_engine": OrchestrationEngine(),
        "execution_engine": ExecutionEngine(),
        "processing_engine": ProcessingEngine(),
        "template_engine": TemplateEngine(),
        "smart_engine": SmartEngine(),
        "adaptive_engine": AdaptiveEngine(),
        "performance_engine": PerformanceEngine(),
        "action_engine": ActionEngine(),
    })

    # ── Layer 3: Services ──
    from .service.background import BackgroundService, DaemonService
    from .service.sync import SyncService, LiveSync, RealtimeSync, StateSync, DataSync
    from .service.update import UpdateService, LiveUpdate, SmartUpdater, SilentUpdater
    from .service.maintenance import MaintenanceService, RecoveryService
    from .service.remote import RemoteService

    registry.update({
        "background_service": BackgroundService(),
        "daemon_service": DaemonService(),
        "sync_service": SyncService(),
        "live_sync": LiveSync(),
        "realtime_sync": RealtimeSync(),
        "state_sync": StateSync(),
        "data_sync": DataSync(),
        "update_service": UpdateService(),
        "live_update": LiveUpdate(),
        "smart_updater": SmartUpdater(),
        "silent_updater": SilentUpdater(),
        "maintenance_service": MaintenanceService(),
        "recovery_service": RecoveryService(),
        "remote_service": RemoteService(),
    })

    # ── Layer 4: Transport ──
    from .transport.bus import EventBus, CommandBus, ServiceBus, UtilityBus
    from .transport.router import TaskRouter, CommandRouter, ActionRouter
    from .transport.dispatcher import Dispatcher, TaskDispatcher, CommandDispatcher, ActionDispatcher
    from .transport.channel import SecureChannel, TransportCore, HiddenChannel

    event_bus = EventBus()
    registry.update({
        "event_bus": event_bus,
        "command_bus": CommandBus(),
        "service_bus": ServiceBus(),
        "utility_bus": UtilityBus(),
        "task_router": TaskRouter(),
        "command_router": CommandRouter(),
        "action_router": ActionRouter(),
        "dispatcher": Dispatcher(),
        "task_dispatcher": TaskDispatcher(),
        "command_dispatcher": CommandDispatcher(),
        "action_dispatcher": ActionDispatcher(),
        "secure_channel": SecureChannel(),
        "transport_core": TransportCore(),
        "hidden_channel": HiddenChannel(),
    })

    # ── Layer 5: Managers ──
    from .manager.plugin import PluginManager as ArchPluginManager, ExtensionManager
    from .manager.task import TaskManager, WorkflowManager, ProcessManager
    from .manager.session import SessionManager, TokenManager
    from .manager.deployment import DeploymentManager, UpdateManager, PackageManager, ArtifactManager

    registry.update({
        "plugin_manager": ArchPluginManager(),
        "extension_manager": ExtensionManager(),
        "task_manager": TaskManager(),
        "workflow_manager": WorkflowManager(),
        "process_manager": ProcessManager(),
        "session_manager": SessionManager(),
        "token_manager": TokenManager(),
        "deployment_manager": DeploymentManager(),
        "update_manager": UpdateManager(),
        "package_manager": PackageManager(),
        "artifact_manager": ArtifactManager(),
    })

    # ── Layer 6: Agents ──
    from .agent.runtime_agent import RuntimeAgent, SyncAgent, UpdateAgent
    from .agent.automation_agent import AutomationAgent, MaintenanceAgent
    from .agent.support import SupportAgent, IntegrationAgent
    from .agent.deployment import DeploymentAgent, EndpointAgent, HostAgent, BridgeAgent

    registry.update({
        "runtime_agent": RuntimeAgent(),
        "sync_agent": SyncAgent(),
        "update_agent": UpdateAgent(),
        "automation_agent": AutomationAgent(),
        "maintenance_agent": MaintenanceAgent(),
        "support_agent": SupportAgent(),
        "integration_agent": IntegrationAgent(),
        "deployment_agent": DeploymentAgent(),
        "endpoint_agent": EndpointAgent(),
        "host_agent": HostAgent(),
        "bridge_agent": BridgeAgent(),
    })

    # ── Layer 6b: Marketing TITAN Agent ──
    try:
        from .agent.marketing_agent import MarketingMasterAgent
        registry["marketing_master_agent"] = MarketingMasterAgent
        logger.info("✅ MarketingMasterAgent registered (init deferred to main)")
    except ImportError:
        logger.debug("MarketingMasterAgent not available")

    # ── Layer 7: Adapters ──
    from .adapter.platform import RemoteAdapter, RuntimeAdapter
    from .adapter.platform import TelegramAdapter
    from .adapter.integration import IntegrationAdapter, CompatibilityAdapter
    from .adapter.transport import InMemoryTransport, SystemAdapter

    registry.update({
        "telegram_adapter": TelegramAdapter(),
        "remote_adapter": RemoteAdapter(),
        "runtime_adapter": RuntimeAdapter(),
        "integration_adapter": IntegrationAdapter("arki"),
        "compatibility_adapter": CompatibilityAdapter(),
        "memory_transport": InMemoryTransport(),
        "system_adapter": SystemAdapter(),
    })

    # ── Layer 8: Bridges ──
    from .bridge.core import BridgeCore, SystemBridge, NativeBridge
    from .bridge.process import ProcessBridge, IPCBridge
    from .bridge.transport_bridge import TransportBridge, StorageBridge
    from .bridge.data import DataBridge

    registry.update({
        "bridge_core": BridgeCore("architecture", "handlers"),
        "system_bridge": SystemBridge(),
        "native_bridge": NativeBridge(),
        "process_bridge": ProcessBridge(),
        "ipc_bridge": IPCBridge(),
        "transport_bridge": TransportBridge(),
        "storage_bridge": StorageBridge(),
        "data_bridge": DataBridge(),
    })

    # ── Layer 9: Monitor ──
    from .monitor.telemetry import TelemetryMonitor, DiagnosticsMonitor
    from .monitor.health import HealthMonitor, Watcher, Observer
    from .monitor.console import (
        RuntimeConsole, AdminConsole, DeveloperConsole,
        ControlPanel, AdminPanel, OperationsPanel, OrchestrationPanel,
    )

    telemetry = TelemetryMonitor()
    diagnostics = DiagnosticsMonitor()
    registry.update({
        "telemetry_monitor": telemetry,
        "diagnostics_monitor": diagnostics,
        "health_monitor": HealthMonitor(),
        "watcher": Watcher(),
        "observer": Observer(),
        "runtime_console": RuntimeConsole(),
        "admin_console": AdminConsole(),
        "developer_console": DeveloperConsole(),
        "control_panel": ControlPanel(),
        "admin_panel": AdminPanel(),
        "operations_panel": OperationsPanel(),
        "orchestration_panel": OrchestrationPanel(),
    })

    # ── Layer 10: Control ──
    from .control.controller import Controller, Coordinator, Supervisor, Operator
    from .control.plane import ControlPlane, RuntimeLayer, ExecutionLayer, OrchestrationLayer

    ctrl_plane = ControlPlane()
    ctrl_plane.add_layer(RuntimeLayer())
    ctrl_plane.add_layer(ExecutionLayer())
    ctrl_plane.add_layer(OrchestrationLayer())
    registry.update({
        "controller": Controller("main"),
        "coordinator": Coordinator(),
        "supervisor": Supervisor(),
        "operator": Operator(),
        "control_plane": ctrl_plane,
    })

    # ── Layer 11: Loaders ──
    from .loader.module import ModuleLoader, RuntimeLoader, AssetLoader
    from .loader.plugin import PluginLoader, ExtensionLoader
    from .loader.bootstrap_loader import BootstrapLoader, PackageLoader, UpdateLoader

    registry.update({
        "module_loader": ModuleLoader(),
        "runtime_loader": RuntimeLoader(),
        "asset_loader": AssetLoader(),
        "plugin_loader": PluginLoader(),
        "extension_loader": ExtensionLoader(),
        "bootstrap_loader": BootstrapLoader(),
        "package_loader": PackageLoader(),
        "update_loader": UpdateLoader(),
    })

    # ── Layer 12: Helpers ──
    from .helper.runtime_helper import RuntimeHelper, ShellHelper, SystemHelper
    from .helper.integration_helper import IntegrationHelper, SetupHelper, DeploymentHelper
    from .helper.support_helper import SupportHelper, AdminHelper, ExecutionHelper
    from .helper.command_helper import CommandHelper, PlatformHelper, RemoteHelper

    registry.update({
        "runtime_helper": RuntimeHelper(),
        "shell_helper": ShellHelper(),
        "system_helper": SystemHelper(),
        "integration_helper": IntegrationHelper(),
        "setup_helper": SetupHelper(),
        "deployment_helper": DeploymentHelper(),
        "support_helper": SupportHelper(),
        "admin_helper": AdminHelper(),
        "execution_helper": ExecutionHelper(),
        "command_helper": CommandHelper(),
        "platform_helper": PlatformHelper(),
        "remote_helper": RemoteHelper(),
    })

    # ── Layer 13: Layers ──
    from .layer.runtime_layer import RuntimeLayerImpl, PlatformLayerImpl
    from .layer.execution_layer import ExecutionLayerImpl
    from .layer.orchestration_layer import OrchestrationLayerImpl, IntegrationLayerImpl
    from .layer.control_layer import ControlLayerImpl

    registry.update({
        "runtime_layer": RuntimeLayerImpl(),
        "platform_layer": PlatformLayerImpl(),
        "execution_layer": ExecutionLayerImpl(),
        "orchestration_layer": OrchestrationLayerImpl(),
        "integration_layer": IntegrationLayerImpl(),
        "control_layer": ControlLayerImpl(),
    })

    # ── Wire cross-component connections ──

    # Feature flags
    config.flags.register("v8_architecture", enabled=True, description="v8 architecture layer")
    config.flags.register("smart_engine", enabled=True, description="AI-adaptive parameters")
    config.flags.register("telemetry", enabled=True, description="Full telemetry collection")
    config.flags.register("hot_reload", enabled=False, description="Hot-reload modules at runtime")

    # Register default config values
    config.define("bot.name", "Arki v9")
    config.define("bot.version", "9.0.0")
    config.define("ai.default_temperature", 0.7)
    config.define("ai.max_tokens", 32768)
    config.define("telemetry.enabled", True)
    config.define("telemetry.flush_interval_s", 300)

    # ── Wire components together (real cross-connections) ──
    from .wiring import wire_components
    wire_components(registry)

    total = len(registry)
    logger.info(
        "✅ Architecture initialized: %d components across 13 layers (wired)", total
    )


    # ── Layer 14: Infrastructure Bridge ──
    try:
        from arki_project.core.boot import get_infra
        infra = get_infra()
        if infra:
            registry["infra_registry"] = infra["registry"]
            registry["infra_orchestrator"] = infra["orchestrator"]
            registry["infra_event_bus"] = infra["event_bus"]
            registry["infra_pipeline"] = infra["pipeline"]
            registry["infra_config"] = infra["config"]
            registry["infra_context_memory"] = infra.get("context_memory")
            registry["infra_gateway_client"] = infra.get("gateway_client")
            logger.info("Architecture ↔ Infrastructure bridge established (%d infra components)",
                       infra["registry"].component_count)
        else:
            logger.warning("Infrastructure not yet booted — bridge skipped")
    except ImportError:
        logger.debug("Infrastructure package not available")

    return registry


# ── Global access ──
_registry: Dict[str, Any] = {}


def get_component(name: str) -> Any:
    """Get an architecture component by name."""
    return _registry.get(name)


def get_registry() -> Dict[str, Any]:
    """Get the full architecture registry."""
    return _registry


def boot_architecture() -> Dict[str, Any]:
    """Boot the architecture and store the registry globally."""
    global _registry
    _registry = init_architecture()
    return _registry


