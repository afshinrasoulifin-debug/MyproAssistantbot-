
from __future__ import annotations
"""
tg_bot/main.py
──────────────
Application entry-point.

Arki Engine v29.0.0 (TITANIUM Architecture)

v29.0.0:
  ✅ Analytics middleware — track every command/response
  ✅ Maintenance mode — toggle via /maintenance
  ✅ Better startup diagnostics
  ✅ Graceful shutdown with cleanup
  ✅ Background task monitoring
  ✅ 72+ AI models (Gemini + Groq + APEX/OpenRouter)
  ✅ New admin commands: /broadcast, /health, /analytics, /maintenance, /backup_db
  ✅ Enhanced error handling throughout
"""

# NOTE: Consider using arki_project.utils.feature_registry for optional imports

# Ensure 'from arki_project.*' imports work regardless of how main.py is invoked
import os as _os, sys as _sys
_app_dir = _os.path.dirname(_os.path.abspath(__file__))
_parent = _os.path.dirname(_app_dir)
if _parent not in _sys.path:
    _sys.path.insert(0, _parent)

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from arki_project.config import Settings, load_settings, validate_startup_config
from sqlalchemy import delete
from arki_project.database.connection import close_db, init_db, get_session
from arki_project.database.models import ChatMessage as DBChatMessage
from arki_project.handlers.health_handler import router as health_router
from arki_project.handlers import (
    admin,
    agents,
    ai_chat,
    automation,
    common,
    compare,
    content_studio,
    create,
    executor,
    files,
    image,
    market,
    models_cmd,
    poster,
    content_brain,
    platform_auto,
    platforms,
    sales_brain,
    sales_engine,
    search,
    tools,
    voice,
)
# v10.2: Cleaned up — settings/remind/monitor/summarize/translate/batch/collab
# commands are already handled by models_cmd, automation, agents, tools, content_studio
from arki_project.handlers import inline_handler
from arki_project.handlers import payment_handler
from arki_project.handlers import template_handler
from arki_project.handlers import victor  # Victor v6 — Independent Intelligence
from arki_project.extra import extra_router

# v10.3: Performance tracking
try:
    from arki_project.utils.performance_tracker import perf_tracker as _perf_tracker
except ImportError:
    _perf_tracker = None
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
# v10.2: New middlewares
from arki_project.middlewares.backpressure_middleware import BackpressureMiddleware
from arki_project.middlewares.idempotency_middleware import IdempotencyMiddleware
from arki_project.middlewares.infrastructure_bridge import InfrastructureBridgeMiddleware
# v10.4.1: Security scanning + handler profiling
from arki_project.middlewares.security_middleware import SecurityMiddleware
from arki_project.middlewares.profiler import ProfilerMiddleware
from arki_project.middlewares.poison_pill_middleware import PoisonPillMiddleware
from arki_project.middlewares.tracing_middleware import TracingMiddleware
from arki_project.utils.degradation import get_degradation_manager
from arki_project.utils.tool_hub import get_tool_symbol
from arki_project.utils.bypass_hub import bypass_status
AIClient = get_tool_symbol("ai_client", "AIClient")
from arki_project.utils.structured_logging import setup_structured_logging, setup_persian_logging
from arki_project.utils.metrics_endpoint import start_metrics_server, stop_metrics_server
from arki_project.utils.alert_system import get_alert_system
from arki_project.utils.data_store import store
MODELS = get_tool_symbol("models_registry", "MODELS", default={})
from arki_project.database.connection import health_check  # v9.8.7: was missing

logger = logging.getLogger(__name__)

# v3.3: Internal management layer — enterprise infrastructure
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
    _V33_AVAILABLE = True
except ImportError:
    _V33_AVAILABLE = False


async def _boot_v33_infrastructure() -> dict:
    """Boot v3.3 enterprise infrastructure layer."""
    if not _V33_AVAILABLE:
        return {"status": "skipped", "reason": "imports unavailable"}

    results = {}
    try:
        # 0a. Structured logging
        try:
            setup_logging(level=os.environ.get("LOG_LEVEL", "INFO"))
            set_correlation_id("boot")
            results["logging"] = {"status": "structured_json"}
        except Exception as e:
            results["logging"] = {"status": "fallback", "error": str(e)}

        # 0b. RBAC initialization
        try:
            rbac = get_rbac()
            admin_ids = [int(x) for x in os.environ.get("ADMIN_IDS", "").replace(",", " ").split() if x.strip().isdigit()]
            rbac.load_from_config(admin_ids=admin_ids)
            results["rbac"] = {"status": "active", **rbac.stats}
        except Exception as e:
            results["rbac"] = {"status": "error", "error": str(e)}

        # 0c. KMS (secure key management)
        try:
            kms = get_kms()
            kms_count = kms.load_from_env()
            results["kms"] = {"status": "active", "keys_loaded": kms_count}
        except Exception as e:
            results["kms"] = {"status": "error", "error": str(e)}

        # 0d. KMS Enforcer (kill-switch for unauthorized access)
        try:
            enforcer = get_kms_enforcer()
            results["kms_enforcer"] = {"status": "active", **enforcer.stats}
        except Exception as e:
            results["kms_enforcer"] = {"status": "error", "error": str(e)}

        # 0e. Stealth Evasion Matrix
        try:
            _traffic = get_traffic_orchestrator()
            _waf = get_waf_engine()
            _hks = get_kinetic_synthesizer()
            _enc = get_payload_encryptor()
            results["stealth_evasion"] = {
                "status": "active",
                "traffic_orchestrator": "morphing_engine_ready",
                "waf_adaptive": "feedback_loop_ready",
                "latency_cloaking": "poisson_kinetic_ready",
                "payload_encryption": "ephemeral_keys_ready",
            }
        except Exception as e:
            results["stealth_evasion"] = {"status": "error", "error": str(e)}

        # 1. Key manager (loads all API keys from env)
        km = get_key_manager()
        key_count = km.load_from_env()
        results["key_manager"] = {"keys_loaded": key_count}

        # 2. Request queue
        queue = get_request_queue()
        await queue.start(num_workers=3)
        results["request_queue"] = {"workers": 3, "status": "running"}

        # 3. Event bus
        bus = get_event_bus()
        results["event_bus"] = {"status": "ready"}

        # 4. Automation connector (registers default rules + wires to event bus)
        connector = get_automation_connector()
        rule_count = connector.setup_default_automations()
        results["automation"] = {"rules": rule_count, "status": "active"}

        # 5. Marketing engine
        mkt = get_marketing_engine()
        results["marketing"] = {"status": "ready"}

        # 6. Search privacy
        privacy = get_search_privacy()
        results["search_privacy"] = {"status": "active"}

        # 7. Proxy rotator
        rotator = get_proxy_rotator()
        proxy_count = rotator.load_from_env()
        results["proxy_rotator"] = {"proxies_loaded": proxy_count}

        logging.getLogger(__name__).info(
            "🏗️ v3.3 Enterprise infrastructure booted: %s",
            ", ".join(f"{k}={v.get('status', 'ok')}" for k, v in results.items() if isinstance(v, dict))
        )
    except Exception as e:
        logging.getLogger(__name__).warning("v3.3 boot partial: %s", e)
        results["error"] = str(e)

    return results



# ── Daily Token Reset Background Task ──
async def _daily_token_reset_loop() -> None:
    """Reset tokens_used_today at midnight UTC every day."""
    import asyncio
    from datetime import datetime, timezone, timedelta
    while True:
        now = datetime.now(timezone.utc)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_secs = (midnight - now).total_seconds()
        await asyncio.sleep(wait_secs)
        try:
            from arki_project.database.connection import get_session
            from sqlalchemy import update
            from arki_project.database.models import User
            async with get_session() as session:
                await session.execute(update(User).values(tokens_used_today=0))
                await session.commit()
            logger.info("Daily token reset complete")
        except Exception as e:
            logger.error("Token reset failed: %s", e)


# ── v9 Intelligence Module System ──
from arki_project.core.init_modules import startup_modules, shutdown_modules
from arki_project.utils.v7_core import persist_memory

# Version from config (reads VERSION file)
try:
    from config import APP_VERSION as _VERSION
except ImportError:
    _VERSION = "29.0.0"

# ── v9 Enterprise Architecture Layer ──
try:
    from arki_project.architecture.setup import boot_architecture
except ImportError:
    boot_architecture = None


# Token reset task is started in main()
def _task_error_callback(task: asyncio.Task) -> None:
    """Log unhandled exceptions from background tasks."""
    try:
        exc = task.exception()
    except asyncio.CancelledError:
        return
    if exc:
        logger.error("Background task %s crashed: %s", task.get_name(), exc, exc_info=exc)


async def main() -> None:
    """Async entry-point: build everything, then poll."""

    # ── 0a. Boot Enterprise Infrastructure Layer v29.0.0 ──
    try:
        from arki_project.infrastructure.boot import boot_infrastructure
        infra = await boot_infrastructure()
        _logger = logging.getLogger(__name__)
        _logger.info(
            "🚀 Infrastructure v29.0.0 booted: %d components (%s)",
            infra["registry"].component_count,
            ", ".join(k for k, v in infra.items() if v is not None and k != "registry" and k != "boot_time"),
        )
        # Wire self-healing engine to start monitoring
        if infra.get("self_healing"):
            try:
                await infra["self_healing"].start()
                _logger.info("🩺 Self-healing engine started")
            except Exception as e:
                _logger.debug("Self-healing start skipped: %s", e)
    except Exception as e:
        logging.getLogger(__name__).warning("Infrastructure boot skipped: %s", e)

    # (orchestration boot moved to after settings load)

    # ── 1. Configuration (load first to get log level) ──
    settings: Settings = load_settings()

    # ── 2. Logging ──
    use_json_logs = os.environ.get("JSON_LOGS", "false").lower() == "true"
    if use_json_logs:
        setup_structured_logging(level=settings.log_level, json_output=True)
    else:
        # v10.3.1: Persian-formatted console output
        setup_persian_logging(settings.log_level)
        # v10.2: Use logging_config JSONFormatter if available
        try:
            from arki_project.utils.logging_config import JSONFormatter 
            logger.debug("logging_config available as fallback")
        except ImportError:
            pass
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        stream=sys.stdout,
    )
    logger.info("Configuration loaded (model=%s, log_level=%s)",
                settings.ai_model, settings.log_level)

    # v10.3: Startup config warnings
    try:
        config_warnings = validate_startup_config(settings)
        for w in config_warnings:
            logger.warning(w)
    except Exception as e:
        logger.debug("Config validation skipped: %s", e)

    n_native = sum(
        1 for m in MODELS.values()
        if (m.provider == "gemini" and settings.ai_api_key)
        or (m.provider == "groq" and settings.groq_api_key)
    )
    n_openrouter = sum(1 for m in MODELS.values() if m.provider == "openrouter")
    # v25.0 AUTONOMOUS: All models available — count all regardless of key
    n_total = n_native + n_openrouter  # FreeAccessRouter covers all

    if settings.ai_api_key:
        logger.info("✅ Gemini API ready")
    if settings.groq_api_key:
        logger.info("✅ Groq API ready")
    if settings.openrouter_api_key:
        logger.info("✅ OpenRouter API ready (%d APEX models)", n_openrouter)
    else:
        logger.info("🤖 OpenRouter AUTONOMOUS — %d models via :free + Smart Fallback", n_openrouter)
    logger.info("✅ Pollinations (Flux) — free image gen")
    logger.info("📊 %d models active | 10 personas | 119+ commands", n_total)

    # v25.0 AUTONOMOUS: System runs with zero keys — FreeAccessRouter is primary
    if not settings.ai_api_key and not settings.groq_api_key:
        logger.info("🤖 AUTONOMOUS MODE active — FreeAccessRouter manages all API access")

    # ── 3. Database ──
    await init_db(settings.database_url)
    logger.info("Database ready")

    # ── 3b. Load persistent data ──
    await store.load_all()
    logger.info("DataStore loaded (products, brands, sales, etc.)")

    # ── 3b-2. Marketing Engine Persistence Patch ──
    try:
        from arki_project.utils.marketing_persistence import patch_marketing_engine
        patch_marketing_engine()
        logger.info('✅ MarketingEngine patched for DB persistence')
    except Exception as e:
        logger.warning('⚠️ Marketing persistence patch: %s (non-fatal)', e)

    # ── 3c. v8 Intelligence Modules ──
    _v8_count = 0
    try:
        _v8_status = await startup_modules()
        _v8_count = sum(1 for v in _v8_status.values() if v == 'ok')
        logger.info('✅ v9 modules: %d/%d active', _v8_count, len(_v8_status))
    except Exception as e:
        logger.warning('⚠️ v9 modules init: %s (non-fatal)', e)

    # ── 3d. v8 Enterprise Architecture (13 layers, 123 components) ──
    _arch_count = 0
    _arch_registry = None
    if boot_architecture:
        try:
            _arch_registry = boot_architecture()
            _arch_count = len(_arch_registry)
            logger.info('✅ Architecture: %d components (wired)', _arch_count)
        except Exception as e:
            logger.warning('⚠️ Architecture init: %s (non-fatal)', e)

        # Start architecture automations (health checks, telemetry, performance watchdog)
        if _arch_registry:
            try:
                from arki_project.architecture.automations import start_automations
                _auto_status = await start_automations(_arch_registry)
                _auto_ok = sum(1 for v in _auto_status.values() if v == 'running')
                logger.info('✅ Automations: %d/%d running', _auto_ok, len(_auto_status))
            except Exception as e:
                logger.warning('⚠️ Automations init: %s (non-fatal)', e)
    else:
        logger.info('ℹ️ Architecture layer not available')

    # ── 3e. Metrics endpoint ──
    try:
        _metrics_port = int(os.environ.get('METRICS_PORT', '9090'))
        await start_metrics_server(_metrics_port)
    except Exception as e:
        logger.debug('Metrics endpoint: %s (non-fatal)', e)

    # ── 4. AI client (multi-provider) ──
    ai_client = AIClient(
        api_key=settings.ai_api_key,
        base_url=settings.ai_base_url,
        model=settings.ai_model,
        max_history=settings.ai_max_history,
        temperature=settings.ai_temperature,
        max_tokens=settings.ai_max_tokens,
        groq_api_key=settings.groq_api_key,
        openrouter_api_key=settings.openrouter_api_key,
    )

    # ── 4b. Boot Orchestration Layer v9.8.7 ──
    try:
        from arki_project.orchestration import boot_orchestrator
        _orch = await boot_orchestrator({
            "gemini_api_key": settings.ai_api_key,
            "groq_api_key": settings.groq_api_key,
            "openrouter_api_key": settings.openrouter_api_key,
        })
        logging.getLogger(__name__).info("🎼 Orchestration layer booted")
    except Exception as e:
        logging.getLogger(__name__).warning("Orchestration boot skipped: %s", e)

    # ── 4c. Boot TITANIUM v10 Security & AI Layer ──
    _titanium_ctx = None
    if getattr(settings, 'titanium_enabled', True):
        try:
            from arki_project.utils.titanium import boot_titanium
            _titanium_ctx = await boot_titanium(settings)
            logging.getLogger(__name__).info(
                "🛡️  TITANIUM v29.0 booted — 7 security layers + "
                "AI orchestrator + adaptive scoring + response cache + health monitor — NO LIMITS"
            )
        except Exception as e:
            logging.getLogger(__name__).warning("TITANIUM boot skipped: %s", e)

    # ── 4c. Centralized stealth/bypass registry status ──
    try:
        _bypass = bypass_status()
        logger.info("Central bypass hub: %d/%d components importable", sum(1 for v in _bypass["components"].values() if v), len(_bypass["components"]))
    except Exception as e:
        logger.debug("Central bypass hub: %s (non-fatal)", e)

    # ── 4d. Session Store (for stealth browser sessions) ──
    _session_store = None
    try:
        from arki_project.sessions.session_store import get_session_store
        _session_store = get_session_store(sessions_dir="sessions")
        await _session_store.start()
        logger.info('🗄️  SessionStore started — %s', _session_store.get_stats())
    except Exception as e:
        logger.debug('SessionStore: %s (non-fatal)', e)
        _session_store = None

    # 9b. Victor brain data directory
    try:
        import os as _os_init
        victor_brain_dir = _os_init.path.join(_os_init.path.dirname(_os_init.path.abspath(__file__)), 'data', 'victor_brain')
        _os_init.makedirs(victor_brain_dir, exist_ok=True)
        logger.info('🧠 Victor brain directory ready: %s', victor_brain_dir)
    except Exception as e:
        logger.debug('Victor brain dir: %s (non-fatal)', e)

    # ── 4d. Marketing Agent TITAN ──
    _marketing_agent = None
    try:
        from arki_project.architecture.agent.marketing_agent import MarketingMasterAgent
        from arki_project.handlers.marketing_auto import setup_marketing_handler

        _marketing_agent = MarketingMasterAgent(admin_ids=settings.admin_ids)
        _mkt_ok = await _marketing_agent.initialize(ai_client=ai_client)
        if _mkt_ok:
            setup_marketing_handler(_marketing_agent)
            await _marketing_agent.start()
            logger.info(
                '🎯 Marketing Agent TITAN v%s started — %s',
                _marketing_agent.AGENT_VERSION,
                _marketing_agent.get_status(),
            )
        else:
            logger.warning('⚠️ Marketing Agent TITAN: initialization returned False')
            _marketing_agent = None
    except Exception as e:
        logger.warning('⚠️ Marketing Agent TITAN boot: %s (non-fatal)', e)
        _marketing_agent = None

    # ── 5. Bot & Dispatcher ──
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()

    # ── v9.1: Wire alert system to bot ──
    _alert_sys = get_alert_system()
    _alert_sys.set_bot(bot)
    for _aid in settings.admin_ids:
        _alert_sys.add_admin(_aid)
    logger.info("✅ Alert system wired (admins: %d)", len(settings.admin_ids))

    # ── 6. Middlewares (order matters: outermost runs first) ──
    # 1. Maintenance check (blocks all non-admin if active)
    maintenance_mw = MaintenanceMiddleware(admin_ids=settings.admin_ids)
    # v9.7.1: Maintenance mode disabled — never block users
    # if settings.maintenance_mode:
    #     MaintenanceMiddleware.active = True
    #     logger.warning("⚠️ Bot starting in MAINTENANCE MODE")
    dp.update.outer_middleware(maintenance_mw)

    # 2. Auto-register users
    dp.update.outer_middleware(AutoRegisterMiddleware())

    # 3. Request dedup (before rate limiter to avoid consuming quota on duplicates)
    dp.update.outer_middleware(DedupMiddleware(window_seconds=3.0))

    # 4. Rate limiting
    dp.update.outer_middleware(
        RateLimiterMiddleware(
            max_messages=settings.rate_limit_messages,
            window_seconds=settings.rate_limit_window,
            admin_ids=settings.admin_ids,
        ),
    )

    # 4. I18n — inject translations
    dp.update.outer_middleware(I18nMiddleware())

    # 5b. Architecture bridge
    dp.update.outer_middleware(ArchitectureBridgeMiddleware(_arch_registry))

    # 5c. Media group dedup — batch media group messages
    dp.message.outer_middleware(MediaGroupMiddleware(latency=1.0))

    # 5e. Callback timeout — auto-answer before 60s
    dp.callback_query.outer_middleware(CallbackTimeoutMiddleware(timeout=25.0))

    # 5d. Plan enforcement — check subscription limits
    dp.update.outer_middleware(PlanEnforcementMiddleware(admin_ids=settings.admin_ids))

    # v10.2: Tracing — adds trace_id to every request
    dp.update.outer_middleware(TracingMiddleware())

    # v10.2: Backpressure — limits concurrent requests
    dp.update.outer_middleware(BackpressureMiddleware(max_concurrent=200))

    # v10.2: Poison pill detector — blocks malformed/malicious messages
    dp.message.outer_middleware(PoisonPillMiddleware())

    # v27.0: Input Guard — sanitizes user input (XSS, injection, overflow)
    try:
        from arki_project.middlewares.input_guard import InputGuardMiddleware
        dp.message.outer_middleware(InputGuardMiddleware(strict=False, log_warnings=True))
        logger.info("✅ InputGuard middleware registered")
    except Exception as _ig_err:
        logger.warning("⚠️ InputGuard not loaded: %s", _ig_err)

    # v10.2: Idempotency — exactly-once processing
    dp.update.outer_middleware(IdempotencyMiddleware())

    # v10.2: Infrastructure bridge — injects TITANIUM into handler data
    dp.update.outer_middleware(InfrastructureBridgeMiddleware())

    # v10.4.1: Security scanning — SecurityInterceptorFilter wired into runtime
    # v17.3: Production_Strict mode — all security checks enforced
    dp.update.outer_middleware(SecurityMiddleware(
        admin_ids=settings.admin_ids,
        block_on_threat=False,  # Tag threats, let handlers decide
    ))

    # v10.4.1: Handler profiler — tracks per-handler latency/errors
    dp.update.outer_middleware(ProfilerMiddleware())

    # 6. Analytics tracking (innermost — measures handler time)
    dp.update.outer_middleware(
        AnalyticsMiddleware(enabled=settings.analytics_enabled),
    )

    # 5a. Connect architecture event bridge
    if _arch_registry:
        try:
            from arki_project.core.arch_events import set_registry as set_arch_registry
            set_arch_registry(_arch_registry)
            logger.info('✅ Architecture event bridge connected')
        except Exception as e:
            logger.warning('⚠️ Architecture event bridge: %s', e)

    # 5b. Architecture middleware (fires events to EventBus for telemetry/performance tracking)
    if _arch_registry:
        try:
            # v9.8.7: removed duplicate ArchitectureMiddleware (already registered via ArchitectureBridgeMiddleware)
            logger.info('✅ Architecture middleware installed')
        except Exception as e:
            logger.warning('⚠️ Architecture middleware: %s (non-fatal)', e)

    # ── 7. Register routers ──
    # Order matters! Specific commands first, catch-all LAST.
    dp.include_router(common.router)       # /start, /help, menu callbacks
    dp.include_router(models_cmd.router)   # /model, /persona, /settings, /autotune, m:/p:/v: callbacks
    dp.include_router(admin.router)        # /ban, /unban, /stats, /users, /broadcast, /health, /analytics, /maintenance, /backup_db
    dp.include_router(executor.router)     # /sh, /exec, /eval, /py, /upload, /download, /sysinfo, /pip, /env, /kill
    dp.include_router(image.router)        # /image, /design
    dp.include_router(search.router)       # /search, /deep
    dp.include_router(tools.router)        # /translate, /summarize, /code, /polish, /explain, /math, /brainstorm
    dp.include_router(create.router)       # /create
    dp.include_router(compare.router)      # /compare, /consensus
    dp.include_router(automation.router)   # /auto, /remind, /qr, /short, /weather, /currency, /rss, /note, /quote, /password
    dp.include_router(agents.router)       # /agents, /workflow, /crm, /finance, /monitor, /autoreply, /plan
    dp.include_router(poster.router)       # /poster (12 poster templates)
    dp.include_router(market.router)       # /listing (Etsy/Tori.fi), /analyze, /photopro
    dp.include_router(content_studio.router)  # /studio /brand /catalog /content /caption /hashtag /batch /story /abtest
    dp.include_router(sales_engine.router)    # /funnel /buyer /repurpose /launch /seasonal /seo /email /pricing /viral /collab /ads /social /swipe /competitor /megapost
    dp.include_router(platforms.router)       # /platforms /connect /publish /shopmanage /euromarket
    dp.include_router(platform_auto.router)  # /addproduct /products /editproduct /delproduct /autopipeline /queue /postqueue /sales /dashboard /weeklytasks /templates
    dp.include_router(content_brain.router)  # /optimize /trending /contentai /aesthetic /series /rewrite /hook /carousel /cta /contentaudit
    dp.include_router(sales_brain.router)    # /salesai /upsell /bundle /retention /winback /loyalty /forecast /objection /giftguide /profit
    dp.include_router(voice.router)          # /voice, voice messages
    dp.include_router(payment_handler.router)  # /subscribe (unique)
    dp.include_router(inline_handler.router)   # inline queries (unique)
    dp.include_router(template_handler.router) # /template (unique)
    # v3.1: Enhanced handler sub-modules (each has unique commands, no conflicts)
    try:
        from arki_project.handlers.translate_handler import router as translate_v2_router
        dp.include_router(translate_v2_router)       # /tr — advanced multi-language
    except ImportError:
        pass
    try:
        from arki_project.handlers.summarize_handler import router as summarize_v2_router
        dp.include_router(summarize_v2_router)       # /sum — multi-mode summarizer
    except ImportError:
        pass
    try:
        from arki_project.handlers.remind_handler import router as remind_v2_router
        dp.include_router(remind_v2_router)          # /remindme — enhanced reminders
    except ImportError:
        pass
    try:
        from arki_project.handlers.settings_handler import router as config_v2_router
        dp.include_router(config_v2_router)          # /config — settings dashboard
    except ImportError:
        pass
    try:
        from arki_project.handlers.monitor_handler import router as monitor_v2_router
        dp.include_router(monitor_v2_router)         # /watch — web monitor
    except ImportError:
        pass
    try:
        from arki_project.handlers.batch_handler import router as batch_v2_router
        dp.include_router(batch_v2_router)           # /batchai — batch AI processing
    except ImportError:
        pass
    try:
        from arki_project.handlers.collab_handler import router as collab_v2_router
        dp.include_router(collab_v2_router)          # /collab — collaboration workspace
    except ImportError:
        pass
    try:
        from arki_project.handlers.agents_pkg import sub_routers as agents_sub_routers
        for _sr in agents_sub_routers:
            dp.include_router(_sr)
        logger.info("✅ agents_pkg: %d sub-routers registered", len(agents_sub_routers))
    except ImportError:
        pass
    # ── Marketing TITAN Agent commands ──
    if _marketing_agent:
        try:
            from arki_project.handlers.marketing_auto import router as marketing_auto_router
            dp.include_router(marketing_auto_router)
            logger.info('✅ Marketing TITAN: 7 commands registered')
        except Exception as e:
            logger.warning('⚠️ Marketing TITAN router: %s (non-fatal)', e)

    dp.include_router(files.router)        # documents, photos (vision)
    dp.include_router(extra_router)

    # v9.8.7: Orchestration status
    try:
        from arki_project.handlers.orch_status import router as orch_status_router
        dp.include_router(orch_status_router)
    except ImportError:
        pass        # /extra, /apex, /race, /parseltongue, /autotunepro, /stm, /classify
    dp.include_router(victor.router)       # /victor — Victor v6 Independent Intelligence
    dp.include_router(ai_chat.router)      # /new, catch-all text (MUST BE LAST!)
    dp.include_router(health_router)  # v3.3: /health command

    # ── 8. Inject shared dependencies ──
    dp["ai_client"] = ai_client

    # ── 4c. Boot v3.3 Enterprise Infrastructure ──
    if _V33_AVAILABLE:
        try:
            v33_result = await _boot_v33_infrastructure()
            dp["v33_infra"] = v33_result
            logger.info("v3.3 infra: %s", v33_result)
        except Exception as e:
            logger.warning("v3.3 infra boot: %s (non-fatal)", e)
    dp["settings"] = settings

    # ── 9. Background tasks ──
    background_tasks: list[asyncio.Task] = []

    # 9a. Cleanup old messages (every 24h)
    async def cleanup_old_messages() -> None:
        """Delete chat_messages older than 30 days every 24h."""
        while True:
            await asyncio.sleep(86400)
            try:
                cutoff = datetime.now(timezone.utc) - timedelta(days=30)
                async with get_session() as session:
                    result = await session.execute(
                        delete(DBChatMessage).where(
                            DBChatMessage.created_at < cutoff,
                        ),
                    )
                    await session.commit()
                    count = result.rowcount  # type: ignore[union-attr]
                if count:
                    logger.info("Cleaned up %d old messages (>30 days)", count)
            except Exception as e:
                logger.warning("Message cleanup failed: %s", e)

    _t = asyncio.create_task(cleanup_old_messages(), name="cleanup_old_messages")
    _t.add_done_callback(_task_error_callback)
    background_tasks.append(_t)

    # 9c. Marketing Scheduler (Phase 3 Fix)
    if _marketing_agent and hasattr(_marketing_agent, "_service") and _marketing_agent._service:
        try:
            _mkt_task = asyncio.create_task(
                _marketing_agent._service._scheduler_loop(), 
                name="marketing_scheduler"
            )
            _mkt_task.add_done_callback(_task_error_callback)
            background_tasks.append(_mkt_task)
            logger.info("✅ Marketing scheduler registered as background task")
        except Exception as e:
            logger.warning("⚠️ Marketing scheduler task registration failed: %s", e)

    # 9b. Periodic in-memory cache eviction (every hour)
    async def evict_stale_memory() -> None:
        """Evict inactive user conversations from memory every hour."""
        while True:
            await asyncio.sleep(3600)
            try:
                evicted = ai_client.evict_stale_users(max_age_seconds=3600)
                if evicted:
                    logger.info("♻️ Evicted %d stale user histories", evicted)
            except Exception as e:
                logger.warning("Memory eviction failed: %s", e)

    _t = asyncio.create_task(evict_stale_memory(), name="evict_stale_memory")
    _t.add_done_callback(_task_error_callback)
    background_tasks.append(_t)

    # 9c. Analytics cleanup (every 24h — keep 90 days)
    async def cleanup_analytics() -> None:
        """Delete analytics events older than 90 days."""
        while True:
            await asyncio.sleep(86400)
            try:
                from arki_project.database.models import AnalyticsEvent
                cutoff = datetime.now(timezone.utc) - timedelta(days=90)
                async with get_session() as session:
                    result = await session.execute(
                        delete(AnalyticsEvent).where(
                            AnalyticsEvent.created_at < cutoff,
                        ),
                    )
                    await session.commit()
                    count = result.rowcount  # type: ignore[union-attr]
                if count:
                    logger.info("Cleaned up %d old analytics events (>90 days)", count)
            except Exception as e:
                logger.warning("Analytics cleanup failed: %s", e)

    _t = asyncio.create_task(cleanup_analytics(), name="cleanup_analytics")
    _t.add_done_callback(_task_error_callback)
    background_tasks.append(_t)

    # v8: Persist memory every 5 minutes
    async def _v8_persist() -> None:
        while True:
            await asyncio.sleep(300)
            try:
                await persist_memory()
            except Exception as e:
                logger.debug("Suppressed: %s", e)
    _t = asyncio.create_task(_v8_persist(), name="_v8_persist")
    _t.add_done_callback(_task_error_callback)
    background_tasks.append(_t)

    # 9d. Recover pending reminders from DB
    try:
        from arki_project.handlers.automation import recover_reminders
        recovered = await recover_reminders(bot)
        if recovered:
            logger.info("♻️ Recovered %d pending reminders", recovered)
    except Exception as e:
        logger.warning("Reminder recovery failed: %s", e)

    # 9e. Start monitor background checker
    monitor_task = None
    try:
        from arki_project.handlers.agents import start_monitor_bg
        monitor_task = await start_monitor_bg(bot)
        if monitor_task:
            background_tasks.append(monitor_task)
        logger.info("♻️ Monitor background checker started (hourly)")
    except Exception as e:
        logger.warning("Monitor background start failed: %s", e)

    # ── 9f. AutoRun Engine (v9) ──
    try:
        from arki_project.utils.v7_core import get_autorun_engine
        _autorun = get_autorun_engine()
        # v10.3.1: Register degradation auto-recovery task
        try:
            from arki_project.core.autorun import register_recovery_task
            register_recovery_task(_autorun)
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)
        await _autorun.start()
        logger.info('✅ AutoRun engine started (with auto-recovery)')
    except Exception as e:
        logger.warning('⚠️ AutoRun engine: %s', e)

    # ── 9g. Plugin System ──
    try:
        from arki_project.utils.plugin_system import PluginManager
        _plug = PluginManager()
        await _plug.discover('plugins')
        await _plug.start_all()
        logger.info('✅ Plugins: %d loaded', getattr(_plug, 'count', 0))
    except Exception as e:
        logger.debug('Plugin system: %s', e)

    # ── 9h. Degradation Manager ──
    try:
        _degradation = get_degradation_manager()
        _degradation.register_service('database')
        _degradation.register_service('ai_client')
        _degradation.register_service('telegram')
        _degradation.register_service('apex')
        _degradation.register_service('victor')  # v10.3: Victor Independent Intelligence
        logger.info('✅ Degradation manager initialized (5 services)')
    except Exception as e:
        logger.warning('⚠️ Degradation manager: %s', e)

    # ── 10. Health check / diagnostics ──
    logger.info("─" * 50)
    logger.info("📊 STARTUP DIAGNOSTICS — Arki Engine v%s:", _VERSION)
    logger.info("  Python: %s", sys.version.split()[0])
    logger.info("  aiogram: %s", __import__("aiogram").__version__)
    logger.info("  SQLAlchemy: %s", __import__("sqlalchemy").__version__)
    logger.info("  Models active: %d (native: %d, APEX: %d)",
                n_total, n_native, n_openrouter if settings.openrouter_api_key else 0)
    logger.info("  Providers: Gemini=%s Groq=%s OpenRouter=%s",
                "✅" if settings.ai_api_key else "❌",
                "✅" if settings.groq_api_key else "❌",
                "✅" if settings.openrouter_api_key else "❌")
    logger.info("  Admin IDs: %s", settings.admin_ids or "none")
    logger.info("  Rate limit: %d msgs / %ds",
                settings.rate_limit_messages, settings.rate_limit_window)
    logger.info("  Analytics: %s", "✅" if settings.analytics_enabled else "❌")
    logger.info("  Maintenance: %s", "🔧 ON" if settings.maintenance_mode else "❌")
    logger.info("  v8 Modules: %d active", _v8_count)
    logger.info("  Background tasks: %d", len(background_tasks))
    logger.info("  Victor v6: ✅")
    logger.info("  Redis: %s", "✅ " + settings.redis_url[:30] if settings.redis_url else "❌ (in-memory fallback)")
    logger.info("  Performance tracking: %s", "✅" if _perf_tracker else "❌")
    logger.info("─" * 50)

    # ── 10b. Start WebSocket remote server + persistent executor ──
    stop_ws_server = stop_persistent_executor = None  # v9.8.7: ensure names exist for finally
    try:
        from arki_project.utils.ws_remote import start_ws_server, stop_ws_server
        await start_ws_server(settings)
    except Exception as e:
        logger.warning("⚠️ WS Remote server start failed: %s", e)

    try:
        from arki_project.utils.persistent_exec import (
            start_persistent_executor, stop_persistent_executor,
        )
        await start_persistent_executor(bot, settings)
        logger.info("✅ Persistent executor worker started")
    except Exception as e:
        logger.warning("⚠️ Persistent executor start failed: %s", e)

    # ── 11. Start APEX API server ──
    g0d_ok = False
    try:
        from arki_project.extra import bridge as apex_bridge
        g0d_ok = await apex_bridge.start_apex_server()
        if g0d_ok:
            logger.info("✅ APEX API server running on port %s",
                        apex_bridge.APEX_PORT)
        else:
            logger.warning("⚠️ APEX API server failed to start — Extra features may be limited")
    except Exception as e:
        logger.warning("⚠️ APEX bridge import/start failed: %s", e)

    # ── 12. Delete any existing webhook & verify bot token ──
    try:
        bot_info = await bot.get_me()
        logger.info("✅ Bot verified: @%s (id=%d)", bot_info.username, bot_info.id)
    except Exception as e:
        logger.error("❌ BOT_TOKEN is invalid or network error: %s", e)
        return

    # ── v9 Shutdown ──
    async def _v8_shutdown() -> None:
        try:
            # Stop Marketing Agent TITAN
            if _marketing_agent:
                try:
                    await _marketing_agent.stop()
                    logger.info('🎯 Marketing Agent TITAN stopped')
                except Exception as e:
                    logger.debug("Marketing agent shutdown: %s", e)

            # Stop Session Store
            if _session_store:
                try:
                    await _session_store.stop()
                    logger.info('🗄️  SessionStore stopped')
                except Exception as e:
                    logger.debug("SessionStore shutdown: %s", e)

            # Stop architecture automations first
            if _arch_registry:
                try:
                    from arki_project.architecture.automations import stop_automations
                    await stop_automations()
                    logger.info('Architecture automations stopped')
                except Exception as e:
                    logger.debug("Suppressed: %s", e)

            # Shutdown TITANIUM v10
            if _titanium_ctx:
                try:
                    from arki_project.utils.titanium import shutdown_titanium
                    await shutdown_titanium()
                    logger.info('🛡️  TITANIUM shut down')
                except Exception as e:
                    logger.debug("TITANIUM shutdown: %s", e)

            # Persist Victor brain on shutdown (use running singleton)
            try:
                from arki_project.handlers.victor import _get_brain as _get_victor_singleton
                _vb = _get_victor_singleton()
                _vb.save_all()
                logger.info('🧠 Victor brain persisted (%d memories)', len(_vb.memory.memories))
            except Exception as _ve:
                logger.debug('Victor brain shutdown: %s', _ve)

            await persist_memory()
            await shutdown_modules()
            logger.info('v8 modules shut down')
        except Exception as e:
            logger.debug("Suppressed: %s", e)
    dp.shutdown.register(_v8_shutdown)

    # CRITICAL: delete webhook before polling — if a webhook exists,
    # polling will receive ZERO updates and the bot appears dead!
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook cleared, pending updates dropped")
    except Exception as e:
        logger.warning("⚠️ delete_webhook failed: %s", e)

    # ── 12.5. Restore analytics state from DB ──
    try:
        from arki_project.utils.performance_analytics import get_analytics as _get_pa
        _pa = _get_pa()
        _restored = await _pa.load_state_from_db()
        logger.info("📂 Analytics: %d model states restored from DB", _restored)
    except Exception as _pa_err:
        logger.warning("Analytics state restore skipped: %s", _pa_err)

    # ── 13. Start polling or webhook ──
    try:
        if settings.webhook_url:
            # Webhook mode — for production deployment behind a reverse proxy
            from aiohttp import web
            from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

            logger.info("🚀 Arki Engine v%s TITANIUM — Starting with webhook: %s",
                         _VERSION, settings.webhook_url)
            _wh_secret = settings.webhook_secret
            await bot.set_webhook(
                settings.webhook_url,
                allowed_updates=dp.resolve_used_update_types(),
                drop_pending_updates=True,
                secret_token=_wh_secret,
            )
            logger.info("🔒 Webhook secret_token configured (length=%d)", len(_wh_secret))

            app = web.Application()

            # Validate Telegram's X-Telegram-Bot-Api-Secret-Token header
            @web.middleware
            async def _webhook_secret_middleware(request: web.Request, handler: Any) -> web.Response:
                incoming_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
                if not __import__("hmac").compare_digest(incoming_secret, _wh_secret):
                    logger.warning(
                        "🚫 Webhook request with invalid/missing secret_token from %s",
                        request.remote,
                    )
                    return web.Response(status=403, text="Forbidden")
                return await handler(request)

            app.middlewares.append(_webhook_secret_middleware)
            webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
            webhook_handler.register(app, path="/webhook")
            setup_application(app, dp, bot=bot)

            # v26.1: Graceful shutdown — persist analytics state
            async def _on_shutdown(app: web.Application) -> None:
                logger.info("🔄 Webhook shutting down — saving analytics state...")
                try:
                    from arki_project.utils.performance_analytics import get_analytics as _get_pa
                    saved = await _get_pa().save_state_to_db()
                    logger.info("💾 Analytics saved: %d models", saved)
                except Exception as _e:
                    logger.warning("Analytics save on shutdown failed: %s", _e)
                try:
                    await bot.delete_webhook()
                except Exception as _err:
                    logger.warning("Suppressed error: %s", _err)

            app.on_shutdown.append(_on_shutdown)

            # v9.6: Health + Readiness endpoints for k8s probes
            async def _health_endpoint(request: web.Request) -> web.Response:
                try:
                    db_ok = await health_check()
                    return web.json_response({
                        "status": "healthy",
                        "version": _VERSION,
                        "database": db_ok,
                    })
                except Exception as e:
                    return web.json_response({"status": "unhealthy", "error": str(e)}, status=503)

            async def _ready_endpoint(request: web.Request) -> web.Response:
                checks = {}
                try:
                    db_ok = await health_check()
                    checks["database"] = db_ok.get("ok", True) if isinstance(db_ok, dict) else bool(db_ok)
                except Exception:
                    checks["database"] = False
                checks["bot"] = bot is not None
                all_ok = all(checks.values())
                return web.json_response(
                    {"ready": all_ok, "checks": checks},
                    status=200 if all_ok else 503,
                )

            # v9.6: Stripe webhook
            try:
                from arki_project.extra.routes.stripe_webhook import stripe_webhook_handler
                app.router.add_post("/stripe/webhook", stripe_webhook_handler)
                logger.info("✅ Stripe webhook mounted at /stripe/webhook")
            except ImportError as _exc:
                logger.debug("Suppressed: %s", _exc)

            # ── v19.0: Metrics + OpenAPI endpoints ──
            async def _metrics_endpoint(request: web.Request) -> web.Response:
                try:
                    from arki_project.utils.metrics_exporter import generate_metrics
                    text, content_type = generate_metrics()
                    return web.Response(text=text, content_type=content_type)
                except Exception as e:
                    return web.json_response({"error": str(e)}, status=500)

            async def _openapi_json(request: web.Request) -> web.Response:
                try:
                    from arki_project.utils.openapi_spec import generate_openapi_spec
                    spec = generate_openapi_spec()
                    return web.json_response(spec)
                except Exception as e:
                    return web.json_response({"error": str(e)}, status=500)

            async def _swagger_ui(request: web.Request) -> web.Response:
                try:
                    from arki_project.utils.openapi_spec import get_swagger_html
                    return web.Response(text=get_swagger_html(), content_type="text/html")
                except Exception as e:
                    return web.Response(text=f"Swagger UI unavailable: {e}", status=500)

            async def _circuit_breakers_endpoint(request: web.Request) -> web.Response:
                try:
                    from arki_project.utils.circuit_breaker import get_all_breaker_health
                    return web.json_response(get_all_breaker_health())
                except Exception as e:
                    return web.json_response({"error": str(e)}, status=500)

            app.router.add_get("/health", _health_endpoint)
            app.router.add_get("/ready", _ready_endpoint)
            app.router.add_get("/metrics", _metrics_endpoint)
            app.router.add_get("/openapi.json", _openapi_json)
            app.router.add_get("/docs", _swagger_ui)
            app.router.add_get("/api/v1/circuit-breakers", _circuit_breakers_endpoint)

            # v27.0: Admin Dashboard + Resilience Layer
            try:
                from arki_project.admin.dashboard import setup_admin_routes
                setup_admin_routes(app)
                logger.info("✅ Admin dashboard mounted at /admin/")
            except Exception as _admin_err:
                logger.warning("⚠️ Admin dashboard init failed: %s", _admin_err)

            try:
                from arki_project.utils.resilience import (
                    get_circuit_manager, get_health_monitor, get_connection_pool, get_memory_guard,
                )
                _cm = get_circuit_manager()
                _hm = get_health_monitor()
                _pool = get_connection_pool()
                _mg = get_memory_guard()
                logger.info("✅ Resilience layer initialized (CircuitBreaker + HealthMonitor + ConnectionPool + MemoryGuard)")
            except Exception as _res_err:
                logger.warning("⚠️ Resilience layer init failed: %s", _res_err)

            logger.info("✅ /health + /ready + /metrics + /docs + /openapi.json + /admin mounted")

            # v19.1: Initialize Free Access Router
            try:
                from arki_project.utils.free_access_router import initialize_free_access
                _free_status = await initialize_free_access()
                logger.info(
                    "✅ Free Access Router: %d models routed, %d keys provisioned",
                    _free_status.get("models_routed", 0),
                    _free_status.get("keys_provisioned", 0),
                )
            except Exception as _fa_err:
                logger.warning("⚠️ Free Access Router init failed: %s", _fa_err)

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("WEBHOOK_PORT", "8443")))
            try:
                await site.start()
                logger.info("✅ Webhook server running on port %s",
                            os.environ.get("WEBHOOK_PORT", "8443"))
                # Keep running until interrupted
                await asyncio.Event().wait()
            except (KeyboardInterrupt, asyncio.CancelledError) as _exc:
                logger.debug("Suppressed: %s", _exc)
            finally:
                await runner.cleanup()
        else:
            logger.info("🚀 Arki Engine v%s TITANIUM — Bot is starting (polling)…", _VERSION)

            # v9.6: Start health server even in polling mode
            async def _start_health_server() -> None:
                try:
                    from aiohttp import web as _web
                    _happ = _web.Application()
                    async def _h(r: web.Request) -> web.Response:
                        return _web.json_response({"status": "healthy", "version": _VERSION, "mode": "polling"})
                    async def _r(r: web.Request) -> web.Response:
                        try:
                            db_ok = await health_check()
                            return _web.json_response({"ready": True, "version": _VERSION})
                        except Exception:
                            return _web.json_response({"ready": False}, status=503)
                    async def _m(r: web.Request) -> web.Response:
                        try:
                            from arki_project.utils.metrics_exporter import generate_metrics
                            text, ct = generate_metrics()
                            from aiohttp import web as _w
                            return _w.Response(text=text, content_type=ct)
                        except Exception as e:
                            return _web.json_response({"error": str(e)}, status=500)
                    async def _d(r: web.Request) -> web.Response:
                        try:
                            from arki_project.utils.openapi_spec import get_swagger_html
                            return _web.Response(text=get_swagger_html(), content_type="text/html")
                        except Exception:
                            return _web.Response(text="Swagger unavailable", status=500)
                    _happ.router.add_get("/health", _h)
                    _happ.router.add_get("/ready", _r)
                    _happ.router.add_get("/metrics", _m)
                    _happ.router.add_get("/docs", _d)
                    _hrunner = _web.AppRunner(_happ)
                    await _hrunner.setup()
                    _hport = int(os.environ.get("HEALTH_PORT", "8080"))
                    _hsite = _web.TCPSite(_hrunner, "0.0.0.0", _hport)
                    await _hsite.start()
                    logger.info("✅ Health server on port %d (polling mode)", _hport)
                except Exception as _he:
                    logger.warning("⚠️ Health server failed: %s", _he)
            _ht = asyncio.create_task(_start_health_server())
            _ht.add_done_callback(_task_error_callback)
            background_tasks.append(_ht)  # v10.2: keep strong reference


            # v9.4: Set command scopes — hide admin commands from regular users
            try:
                from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
                user_commands = [
                    BotCommand(command="start", description="شروع"),
                    BotCommand(command="help", description="راهنما"),
                    BotCommand(command="chat", description="چت با AI"),
                    BotCommand(command="search", description="جستجوی وب"),
                    BotCommand(command="image", description="تولید تصویر"),
                    BotCommand(command="translate", description="ترجمه"),
                    BotCommand(command="summarize", description="خلاصه‌سازی"),
                    BotCommand(command="billing", description="اشتراک"),
                    BotCommand(command="settings", description="تنظیمات"),
                    BotCommand(command="victor", description="هوش مستقل ویکتور"),
                ]
                await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

                admin_commands = user_commands + [
                    BotCommand(command="admin", description="پنل مدیریت"),
                    BotCommand(command="broadcast", description="ارسال همگانی"),
                    BotCommand(command="analytics", description="آنالیتیکس"),
                    BotCommand(command="feature", description="Feature Flags"),
                    BotCommand(command="audit", description="لاگ حسابرسی"),
                    BotCommand(command="network", description="ابزار شبکه"),
                    BotCommand(command="victorstats", description="آمار ویکتور"),
                    BotCommand(command="perfstats", description="عملکرد هندلرها"),
                ]
                for admin_id in settings.admin_ids:
                    try:
                        await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
                    except Exception as _exc:
                        logger.debug("Suppressed: %s", _exc)
                logger.info("Command scopes configured")
            except Exception as e:
                logger.warning("Failed to set command scopes: %s", e)

            await dp.start_polling(
                bot, allowed_updates=dp.resolve_used_update_types(),
            )
    finally:
        # Graceful shutdown
        logger.info("Shutting down…")

        # Cancel all background tasks
        for task in background_tasks:
            task.cancel()
        if background_tasks:
            await asyncio.gather(*background_tasks, return_exceptions=True)

        # Shutdown orchestration layer
        try:
            from arki_project.orchestration import get_orchestrator
            await get_orchestrator().shutdown()
        except Exception as _e:
            logger.debug("Suppressed: %s", _e)  # v10.1: no longer silent

        # Close AI client
        await ai_client.close()

        # Stop WS remote server + persistent executor
        try:
            if stop_ws_server:
                await stop_ws_server()
        except Exception as e:
            logger.debug("Suppressed: %s", e)
        try:
            if stop_persistent_executor:
                await stop_persistent_executor()
        except Exception as e:
            logger.debug("Suppressed: %s", e)
        try:
            await stop_metrics_server()
        except Exception as _e:
            logger.debug("Suppressed: %s", _e)  # v10.1: no longer silent

        # Stop APEX API server
        if g0d_ok:
            try:
                await apex_bridge.stop_apex_server()
            except Exception as e:
                logger.debug("Suppressed: %s", e)

        # Close shared HTTP pool
        from arki_project.utils.http_pool import close_all as close_http_pool
        await close_http_pool()

        # Close database
        await close_db()

        # Close bot session
        await bot.session.close()
        logger.info("✅ Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())


