
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
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
from arki_project.handlers import *  # auto-fixed
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
    """Boot enterprise infrastructure. See main_parts/boot_infrastructure.py."""
    from main_parts.boot_infrastructure import _boot_v33_infrastructure as _impl
    return await _impl()

# ── Daily Token Reset Background Task ──
async def _daily_token_reset_loop() -> None:
    """Daily token reset. See main_parts/background_tasks.py."""
    from main_parts.background_tasks import _daily_token_reset_loop as _impl
    await _impl()

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
from main_parts.background_tasks import _task_error_callback  # noqa

# ── Extracted helper functions (implementations in main_parts/) ──

async def _register_all_middlewares(dp, bot, settings):
    """Register all middlewares. See main_parts/middleware_setup.py for full code."""
    from main_parts.middleware_setup import register_middlewares
    await register_middlewares(dp, bot, settings)


async def _register_all_routers(dp, bot, settings):
    """Register all routers. See main_parts/router_setup.py for full code."""
    from main_parts.router_setup import register_routers
    await register_routers(dp, bot, settings)


async def _start_all_background_tasks(bot, settings, background_tasks):
    """Start background tasks. See main_parts/background_bootstrap.py for full code."""
    from main_parts.background_bootstrap import start_background_tasks
    await start_background_tasks(bot, settings, background_tasks)

async def main() -> None:
    """Async entry-point: build everything, then poll."""

    # ── Sections 0a-3e: Core services (see main_parts/core_init.py) ──
    try:
        from main_parts.core_init import init_core_services
        await init_core_services(settings)
    except Exception as exc:
        logger.warning("Core services init: %s", exc)

    # ── Sections 4-4d: AI layer (see main_parts/ai_init.py) ──
    try:
        from main_parts.ai_init import init_ai_layer
        ai_client = await init_ai_layer(settings)
    except Exception as exc:
        logger.warning("AI layer init: %s", exc)
        ai_client = None

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

    # ── 6. Middlewares (see main_parts/middleware_setup.py) ──
    await _register_all_middlewares(dp, bot, settings)

    # ── 7. Register routers (see main_parts/router_setup.py) ──
    await _register_all_routers(dp, bot, settings)

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

    # ── 9. Background tasks (see main_parts/background_bootstrap.py) ──
    await _start_all_background_tasks(bot, settings, background_tasks)

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
        from arki_project.utils.persistent_exec import start_persistent_executor, stop_persistent_executor
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
        else:
            # Polling mode (handled by run_bot.py)
            logger.info("No webhook URL configured — use run_bot.py for polling mode")
    except Exception as _main_exc:
        logger.error("Startup error: %s", _main_exc, exc_info=True)

    # ── v19.0: Metrics + OpenAPI (see main_parts/metrics_api.py) ──
    try:
        from main_parts.metrics_api import init_metrics_api
        await init_metrics_api(bot, settings, ai_client)
    except Exception as exc:
        logger.warning("Metrics API init: %s", exc)

if __name__ == "__main__":
    asyncio.run(main())

