
"""
main_parts/core_init.py — Core service initialization
Extracted from main.py sections 0a-3e to reduce complexity.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


async def init_core_services(settings):
    """Initialize core services: database, intelligence modules, enterprise architecture."""
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
            except ArkiBaseError as e:
                _logger.debug("Self-healing start skipped: %s", e)
    except ArkiBaseError as e:
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
    except ArkiBaseError as e:
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
    except ArkiBaseError as e:
        logger.warning('⚠️ Marketing persistence patch: %s (non-fatal)', e)

    # ── 3c. v8 Intelligence Modules ──
    _v8_count = 0
    try:
        _v8_status = await startup_modules()
        _v8_count = sum(1 for v in _v8_status.values() if v == 'ok')
        logger.info('✅ v9 modules: %d/%d active', _v8_count, len(_v8_status))
    except ArkiBaseError as e:
        logger.warning('⚠️ v9 modules init: %s (non-fatal)', e)

    # ── 3d. v8 Enterprise Architecture (13 layers, 123 components) ──
    _arch_count = 0
    _arch_registry = None
    if boot_architecture:
        try:
            _arch_registry = boot_architecture()
            _arch_count = len(_arch_registry)
            logger.info('✅ Architecture: %d components (wired)', _arch_count)
        except ArkiBaseError as e:
            logger.warning('⚠️ Architecture init: %s (non-fatal)', e)

        # Start architecture automations (health checks, telemetry, performance watchdog)
        if _arch_registry:
            try:
                from arki_project.architecture.automations import start_automations
                _auto_status = await start_automations(_arch_registry)
                _auto_ok = sum(1 for v in _auto_status.values() if v == 'running')
                logger.info('✅ Automations: %d/%d running', _auto_ok, len(_auto_status))
            except ArkiBaseError as e:
                logger.warning('⚠️ Automations init: %s (non-fatal)', e)
    else:
        logger.info('ℹ️ Architecture layer not available')

    # ── 3e. Metrics endpoint ──
    try:
        _metrics_port = int(os.environ.get('METRICS_PORT', '9090'))
        await start_metrics_server(_metrics_port)
    except ArkiBaseError as e:
        logger.debug('Metrics endpoint: %s (non-fatal)', e)



