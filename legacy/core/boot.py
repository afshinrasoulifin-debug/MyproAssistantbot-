
from __future__ import annotations
"""
core/boot.py — Boot the entire infrastructure layer v29.0.0
════════════════════════════════════════════════════════════════════
Resilient startup: every import is guarded so a missing module
never crashes the whole boot sequence.

v10.4.1: Deep structural upgrade
  - Self-healing engine wired in
  - Observability layer initialized
  - Database optimizer connected
  - Handler profiler registered
  - Component health monitoring active
  - Alert rules for critical systems
"""
import importlib
import logging
import time

logger = logging.getLogger(__name__)

_infra_context = None


def get_infra() -> object:
    """Get the booted infrastructure context (singleton)."""
    return _infra_context


def _safe_import(module_path: str, class_name: str) -> type | None:
    """Import a class safely; return None if module doesn't exist."""
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, class_name)
    except Exception as exc:
        logger.debug("Skip %s.%s: %s", module_path, class_name, exc)
        return None


async def boot_infrastructure() -> None:
    """Initialize all infrastructure components and wire them together.

    Every combined module is loaded resiliently — if it doesn't exist,
    boot continues without it.
    """
    global _infra_context
    t0 = time.time()

    from arki_project.core.registry import InfraRegistry

    # ── Combined Patterns: resilient loading ──
    combined_specs = [
        ("mega_orchestrator",           "MegaOrchestrator"),
        ("full_stack_pipeline",         "FullStackPipeline"),
        ("event_bus_dispatcher",        "EventBusDispatcher"),
        ("dynamic_config_flags",        "DynamicConfigFlags"),
        ("context_sync_memory",         "ContextSyncMemory"),
        ("batch_worker_queue",          "BatchWorkerQueue"),
        ("inference_gateway_cache",     "InferenceGatewayCache"),
        ("edge_runtime_proxy",          "EdgeRuntimeProxy"),
        ("cloud_gateway_multi",         "CloudGatewayMulti"),
        ("runtime_bridge_orchestrator", "RuntimeBridgeOrchestrator"),
        ("model_router_registry",       "ModelRouterRegistry"),
        ("workflow_engine_scheduler",   "WorkflowEngineScheduler"),
        ("multi_provider_aggregator",   "MultiProviderAggregator"),
        ("relay_transport_bridge",      "RelayTransportBridge"),
        ("plugin_system_loader",        "PluginSystemLoader"),
        ("provider_pool_shadow",        "ProviderPoolShadow"),
        ("prompt_runtime_optimizer",    "PromptRuntimeOptimizer"),
        ("ai_hub_connector",           "AIHubConnector"),
        ("ai_gateway_unified_client",  "AIGatewayUnifiedClient"),
        ("smart_router_adaptive",      "SmartRouterAdaptive"),
        ("smart_proxy_fallback",       "SmartProxyFallback"),
        ("automation_layer_router",    "AutomationLayerRouter"),
        ("assistant_agent_session",    "AssistantAgentSession"),
    ]

    registry = InfraRegistry()
    loaded = 0
    for module_name, class_name in combined_specs:
        full_path = f"arki_project.infrastructure.combined.{module_name}"
        cls = _safe_import(full_path, class_name)
        if cls:
            try:
                instance = cls()
                registry.register(module_name, instance)
                loaded += 1
            except Exception as exc:
                logger.debug("Cannot instantiate %s: %s", class_name, exc)

    registry.auto_register()

    # ── Initialize Self-Healing Engine ──
    self_healing = None
    try:
        from arki_project.core.self_healing import SelfHealingEngine
        self_healing = SelfHealingEngine(check_interval=30.0)
        registry.register("self_healing", self_healing)
        logger.info("Self-healing engine loaded")
    except Exception as e:
        logger.debug("Self-healing engine skipped: %s", e)

    # ── Initialize Observability Layer ──
    observability = None
    try:
        from arki_project.core.observability import get_observability
        observability = get_observability()
        registry.register("observability", observability)
        logger.info("Observability layer loaded")
    except Exception as e:
        logger.debug("Observability layer skipped: %s", e)

    # ── Initialize Database Optimizer ──
    db_optimizer = None
    try:
        from arki_project.database.optimizer import get_db_optimizer
        db_optimizer = get_db_optimizer()
        registry.register("db_optimizer", db_optimizer)
        logger.info("Database optimizer loaded")
    except Exception as e:
        logger.debug("Database optimizer skipped: %s", e)

    # ── Initialize Handler Profiler ──
    profiler = None
    try:
        from arki_project.middlewares.profiler import get_profiler
        profiler = get_profiler()
        registry.register("handler_profiler", profiler)
        logger.info("Handler profiler loaded")
    except Exception as e:
        logger.debug("Handler profiler skipped: %s", e)

    # ── Wire up alert rules (if both self_healing + observability exist) ──
    if observability and self_healing:
        try:
            from arki_project.core.observability import AlertRule, AlertSeverity
            # Alert: high error rate
            observability.alerts.add_rule(AlertRule(
                name="high_error_rate",
                condition=lambda: observability.metrics.counter("errors.total") > 100,
                severity=AlertSeverity.WARNING,
                message="Total errors exceeded 100",
                cooldown_seconds=600,
            ))
            # Alert: system unhealthy
            observability.alerts.add_rule(AlertRule(
                name="system_unhealthy",
                condition=lambda: not self_healing.is_system_healthy,
                severity=AlertSeverity.CRITICAL,
                message="Self-healing reports unhealthy components",
                cooldown_seconds=120,
            ))
        except Exception as e:
            logger.debug("Alert wiring skipped: %s", e)

    _infra_context = {
        "registry": registry,
        "self_healing": self_healing,
        "observability": observability,
        "db_optimizer": db_optimizer,
        "handler_profiler": profiler,
        "boot_time": time.time() - t0,
    }

    elapsed = time.time() - t0
    logger.info(
        "Infrastructure booted in %.1fms — %d combined + %d auto-discovered = %d total (%s)",
        elapsed * 1000, loaded, registry.component_count - loaded,
        registry.component_count,
        ", ".join(filter(None, [
            "self-healing" if self_healing else None,
            "observability" if observability else None,
            "db-optimizer" if db_optimizer else None,
            "profiler" if profiler else None,
        ]))
    )
    return _infra_context


