
from __future__ import annotations
"""
boot/imports.py — Centralized Import Management
═══════════════════════════════════════════════════
Arki Engine v29.0.0

Provides lazy-loaded imports for main.py to reduce startup coupling.
All handler and middleware imports are deferred until needed.
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def get_handler_routers() -> Any:
    """Lazily import and return all handler routers."""
    from arki_project.handlers import (
        admin, agents, ai_chat, automation, common, compare,
        content_studio, create, executor, files, image, market,
        models_cmd, poster, content_brain, platform_auto, platforms,
        sales_brain, sales_engine, search, tools, voice,
    )
    from arki_project.handlers import inline_handler, payment_handler, template_handler
    from arki_project.handlers import victor
    from arki_project.handlers.health_handler import router as health_router
    from arki_project.extra import extra_router
    
    return {
        "common": common.router,
        "admin": admin.router,
        "models_cmd": models_cmd.router,
        "content_studio": content_studio.router,
        "content_brain": content_brain.router,
        "sales_engine": sales_engine.router,
        "sales_brain": sales_brain.router,
        "automation": automation.router,
        "executor": executor.router,
        "agents": agents.router,
        "tools": tools.router,
        "voice": voice.router,
        "files": files.router,
        "search": search.router,
        "image": image.router,
        "poster": poster.router,
        "create": create.router,
        "compare": compare.router,
        "market": market.router,
        "platforms": platforms.router,
        "platform_auto": platform_auto.router,
        "inline_handler": inline_handler.router,
        "payment_handler": payment_handler.router,
        "template_handler": template_handler.router,
        "victor": victor.router,
        "health": health_router,
        "extra": extra_router,
        # ai_chat must be LAST
        "ai_chat": ai_chat.router,
    }


def get_middleware_classes() -> Any:
    """Lazily import and return all middleware classes."""
    from arki_project.middlewares.analytics import AnalyticsMiddleware
    from arki_project.middlewares.maintenance import MaintenanceMiddleware
    from arki_project.middlewares.rate_limiter import RateLimiterMiddleware
    from arki_project.middlewares.register import AutoRegisterMiddleware
    from arki_project.middlewares.i18n_middleware import I18nMiddleware
    from arki_project.middlewares.architecture_bridge import ArchitectureBridgeMiddleware
    from arki_project.middlewares.dedup_middleware import DedupMiddleware
    from arki_project.middlewares.plan_enforcement_middleware import PlanEnforcementMiddleware
    from arki_project.middlewares.callback_timeout_middleware import CallbackTimeoutMiddleware
    from arki_project.middlewares.media_group_middleware import MediaGroupMiddleware
    from arki_project.middlewares.backpressure_middleware import BackpressureMiddleware
    from arki_project.middlewares.idempotency_middleware import IdempotencyMiddleware
    from arki_project.middlewares.infrastructure_bridge import InfrastructureBridgeMiddleware
    from arki_project.middlewares.security_middleware import SecurityMiddleware
    from arki_project.middlewares.profiler import ProfilerMiddleware
    from arki_project.middlewares.poison_pill_middleware import PoisonPillMiddleware
    from arki_project.middlewares.tracing_middleware import TracingMiddleware
    
    return {
        "AnalyticsMiddleware": AnalyticsMiddleware,
        "MaintenanceMiddleware": MaintenanceMiddleware,
        "RateLimiterMiddleware": RateLimiterMiddleware,
        "AutoRegisterMiddleware": AutoRegisterMiddleware,
        "I18nMiddleware": I18nMiddleware,
        "ArchitectureBridgeMiddleware": ArchitectureBridgeMiddleware,
        "DedupMiddleware": DedupMiddleware,
        "PlanEnforcementMiddleware": PlanEnforcementMiddleware,
        "CallbackTimeoutMiddleware": CallbackTimeoutMiddleware,
        "MediaGroupMiddleware": MediaGroupMiddleware,
        "BackpressureMiddleware": BackpressureMiddleware,
        "IdempotencyMiddleware": IdempotencyMiddleware,
        "InfrastructureBridgeMiddleware": InfrastructureBridgeMiddleware,
        "SecurityMiddleware": SecurityMiddleware,
        "ProfilerMiddleware": ProfilerMiddleware,
        "PoisonPillMiddleware": PoisonPillMiddleware,
        "TracingMiddleware": TracingMiddleware,
    }


def get_infrastructure_components() -> Any:
    """Lazily import enterprise infrastructure components.
    
    Returns (components_dict, available: bool)
    """
    try:
        from arki_project.utils.internal_api_gateway import get_api_gateway
        from arki_project.utils.event_bus import get_event_bus
        from arki_project.utils.automation_connector import get_automation_connector
        from arki_project.utils.marketing_engine import get_marketing_engine
        from arki_project.utils.search_privacy import get_search_privacy
        from arki_project.utils.proxy_rotator import get_proxy_rotator
        from arki_project.utils.request_queue import get_request_queue
        from arki_project.utils.api_key_manager import get_key_manager
        from arki_project.utils.kms import get_kms
        from arki_project.utils.traffic_orchestrator import get_traffic_orchestrator
        from arki_project.utils.waf_adaptive import get_waf_engine
        from arki_project.utils.latency_cloaking import get_kinetic_synthesizer
        from arki_project.utils.payload_encryption import get_payload_encryptor
        from arki_project.utils.kms_enforcer import get_kms_enforcer
        from arki_project.utils.preflight import run_preflight
        from arki_project.utils.rbac import get_rbac, Role
        from arki_project.utils.structured_logging import setup_logging, set_correlation_id
        
        return {
            "api_gateway": get_api_gateway,
            "event_bus": get_event_bus,
            "automation_connector": get_automation_connector,
            "marketing_engine": get_marketing_engine,
            "search_privacy": get_search_privacy,
            "proxy_rotator": get_proxy_rotator,
            "request_queue": get_request_queue,
            "key_manager": get_key_manager,
            "kms": get_kms,
            "traffic_orchestrator": get_traffic_orchestrator,
            "waf_engine": get_waf_engine,
            "kinetic_synthesizer": get_kinetic_synthesizer,
            "payload_encryptor": get_payload_encryptor,
            "kms_enforcer": get_kms_enforcer,
            "run_preflight": run_preflight,
            "get_rbac": get_rbac,
            "Role": Role,
            "setup_logging": setup_logging,
            "set_correlation_id": set_correlation_id,
        }, True
    except ImportError:
        logger.debug("Enterprise infrastructure layer not available")
        return {}, False


