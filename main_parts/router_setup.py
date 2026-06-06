
"""main_parts/router_setup.py — Router registration extracted from main()"""
from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def register_routers(dp: Any, bot: Any, settings: Any) -> None:
    """Register all routers on the dispatcher."""
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
        except ArkiBaseError as e:
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



