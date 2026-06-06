
"""
main_parts/ai_init.py — AI layer initialization
Extracted from main.py sections 4-4d to reduce complexity.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


async def init_ai_layer(settings):
    """Initialize AI client, orchestration, TITANIUM, stealth, marketing."""
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
    except ArkiBaseError as e:
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
        except ArkiBaseError as e:
            logging.getLogger(__name__).warning("TITANIUM boot skipped: %s", e)

    # ── 4c. Centralized stealth/bypass registry status ──
    try:
        _bypass = bypass_status()
        logger.info("Central bypass hub: %d/%d components importable", sum(1 for v in _bypass["components"].values() if v), len(_bypass["components"]))
    except ArkiBaseError as e:
        logger.debug("Central bypass hub: %s (non-fatal)", e)

    # ── 4d. Session Store (for stealth browser sessions) ──
    _session_store = None
    try:
        from arki_project.sessions.session_store import get_session_store
        _session_store = get_session_store(sessions_dir="sessions")
        await _session_store.start()
        logger.info('🗄️  SessionStore started — %s', _session_store.get_stats())
    except ArkiBaseError as e:
        logger.debug('SessionStore: %s (non-fatal)', e)
        _session_store = None

    # 9b. Victor brain data directory
    try:
        import os as _os_init
        victor_brain_dir = _os_init.path.join(_os_init.path.dirname(_os_init.path.abspath(__file__)), 'data', 'victor_brain')
        _os_init.makedirs(victor_brain_dir, exist_ok=True)
        logger.info('🧠 Victor brain directory ready: %s', victor_brain_dir)
    except ArkiBaseError as e:
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
    except ArkiBaseError as e:
        logger.warning('⚠️ Marketing Agent TITAN boot: %s (non-fatal)', e)
        _marketing_agent = None



