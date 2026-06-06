
from __future__ import annotations
"""
tg_bot/core/init_modules.py — Module Lifecycle Manager v2.0
═══════════════════════════════════════════════════════════════
Initialize, health-check, and gracefully shutdown all v8/v9 modules.

Called from main.py:
    from arki_project.core.init_modules import startup_modules, shutdown_modules

v2.0: Fixed module paths (arki_project), corrected class names,
      removed non-existent modules, added resilient loading.
"""


import importlib
import logging
import os
import time

logger = logging.getLogger(__name__)


async def startup_modules() -> dict:
    """
    Initialize all intelligence modules via v7_core singletons.
    Returns status dict for monitoring.
    """
    start = time.time()
    status = {}

    # ── Phase A: Singleton getters via v7_core ──
    singleton_inits = [
        ("memory_store",     "arki_project.utils.v7_core", "get_memory"),
        ("telemetry",        "arki_project.utils.v7_core", "get_telemetry"),
        ("prompt_engine",    "arki_project.utils.v7_core", "get_prompt_engine"),
        ("data_analyzer",    "arki_project.utils.v7_core", "get_analyzer"),
        ("text_transform",   "arki_project.utils.v7_core", "get_transformer"),
        ("web_recon",        "arki_project.utils.v7_core", "get_web_recon"),
        ("multi_llm",        "arki_project.utils.v7_core", "get_multi_llm"),
        ("agent_executor",   "arki_project.utils.v7_core", "get_agent_executor"),
        ("workflow_engine",  "arki_project.utils.v7_core", "get_workflow_engine"),
        ("marketing_engine", "arki_project.utils.v7_core", "get_marketing_engine"),
        ("autorun_engine",   "arki_project.utils.v7_core", "get_autorun_engine"),
    ]

    # ── Phase B: Direct class imports (modules that need custom init) ──
    additional_modules = [
        ("pipeline",       "arki_project.core.pipeline",               "IntelligentPipeline",  {}),
        ("reasoning",      "arki_project.core.reasoning",              "ReasoningEngine",      {}),
        ("autotune",       "arki_project.utils.autotune",              None,                   {}),  # needs ParameterSpace — import-only check
        ("web_search",     "arki_project.utils.web_search",            "WebSearchEngine",      {}),
        ("crypto",         "arki_project.utils.crypto_engine",         None,                   {}),
        ("network",        "arki_project.utils.network_tools",         "NetworkToolsEngine",   {}),
        ("integration",    "arki_project.utils.integration_hub",       "ConnectorRegistry",    {}),
        ("multimodal",     "arki_project.utils.multimodal_engine",     "MultimodalEngine",     {}),
        ("terminal",       "arki_project.utils.terminal_emulator",     "TerminalEmulator",     {}),
        ("victor_brain",   "arki_project.handlers.victor",             "VictorBrain",          {}),
        ("victor_db",      "arki_project.utils.victor_db_backend",     "VictorDB",             {"db_path": os.path.join("data", "victor.db")}),
        ("orchestrator",   "arki_project.utils.master_orchestrator",   "MasterOrchestrator",   {}),
        ("dashboard",      "arki_project.utils.dashboard_monitor",     "MetricsRegistry",      {}),
        ("plugin",         "arki_project.utils.plugin_system",         "PluginManager",        {}),
        ("jina_reader",    "arki_project.utils.jina_reader",           None,                   {}),
        ("voice_stt",      "arki_project.utils.voice_stt",             None,                   {}),
    ]

    loaded = 0

    # Init singletons
    for name, mod_path, getter_name in singleton_inits:
        try:
            mod = importlib.import_module(mod_path)
            getter = getattr(mod, getter_name)
            getter()  # First call creates the singleton
            status[name] = "ok"
            loaded += 1
        except Exception as exc:
            status[name] = f"warn: {exc}"
            logger.debug("Singleton %s init: %s", name, exc)

    # Init additional modules
    for name, mod_path, class_name, kwargs in additional_modules:
        try:
            mod = importlib.import_module(mod_path)
            if class_name:
                getattr(mod, class_name)(**kwargs)
            status[name] = "ok"
            loaded += 1
        except Exception as exc:
            status[name] = f"warn: {exc}"
            logger.debug("Module %s init: %s", name, exc)

    elapsed = time.time() - start
    total = len(singleton_inits) + len(additional_modules)
    logger.info(
        "✅ Module startup: %d/%d loaded in %.2fs", loaded, total, elapsed
    )

    return status


async def shutdown_modules() -> None:
    """Graceful shutdown — persist memory."""
    try:
        from arki_project.utils.v7_core import persist_memory
        await persist_memory()
    except Exception as e:
        logger.debug("Shutdown persist: %s", e)
    logger.info("Module shutdown complete.")


