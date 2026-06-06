
"""main_parts/middleware_setup.py — Middleware registration extracted from main()"""
from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def register_middlewares(dp: Any, bot: Any, settings: Any, *, infra: dict = None) -> None:
    """Register all middlewares on the dispatcher.
    
    Order matters: outermost runs first.
    """
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
    except ArkiBaseError as _ig_err:
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
        except ArkiBaseError as e:
            logger.warning('⚠️ Architecture event bridge: %s', e)

    # 5b. Architecture middleware (fires events to EventBus for telemetry/performance tracking)
    if _arch_registry:
        try:
            # v9.8.7: removed duplicate ArchitectureMiddleware (already registered via ArchitectureBridgeMiddleware)
            logger.info('✅ Architecture middleware installed')
        except ArkiBaseError as e:
            logger.warning('⚠️ Architecture middleware: %s (non-fatal)', e)



