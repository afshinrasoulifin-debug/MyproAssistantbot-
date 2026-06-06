
from __future__ import annotations
"""
utils.tool_hub — canonical shared access point for modularized tools.

This module is intentionally small and side-effect-light.  Large legacy modules
remain import-compatible, but runtime code can branch from this hub to avoid
scattered direct imports and duplicate feature selection logic.
"""

import importlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    canonical_module: str
    legacy_module: str | None = None
    symbols: tuple[str, ...] = ()
    description: str = ""


_TOOL_SPECS: dict[str, ToolSpec] = {
    "ai_client": ToolSpec("ai_client", "arki_project.utils.ai_client_pkg", "arki_project.utils.ai_client", ("AIClient",), "multi-provider AI client"),
    "free_access_router": ToolSpec("free_access_router", "arki_project.utils.free_access_router_pkg", "arki_project.utils.free_access_router", ("FreeAccessRouter", "free_router"), "free/fallback model routing"),
    "agent_executor": ToolSpec("agent_executor", "arki_project.utils.agent_executor_pkg", "arki_project.utils.agent_executor", ("AgentExecutor",), "agent execution utilities"),
    "autotune": ToolSpec("autotune", "arki_project.utils.autotune_pkg", "arki_project.utils.autotune", (), "model and prompt autotuning"),
    "multi_llm_orchestrator": ToolSpec("multi_llm_orchestrator", "arki_project.utils.multi_llm_orchestrator_pkg", "arki_project.utils.multi_llm_orchestrator", ("MultiLLMOrchestrator",), "multi-model orchestration"),
    "models_registry": ToolSpec("models_registry", "arki_project.utils.models_registry_pkg", "arki_project.utils.models_registry", ("MODELS",), "AI model registry"),
    "memory_store": ToolSpec("memory_store", "arki_project.utils.memory_store_pkg", "arki_project.utils.memory_store", (), "persistent memory store"),
    "text_transform": ToolSpec("text_transform", "arki_project.utils.text_transform_pkg", "arki_project.utils.text_transform", (), "text processing helpers"),
    "workflow_engine": ToolSpec("workflow_engine", "arki_project.utils.workflow_engine_pkg", "arki_project.utils.workflow_engine", (), "workflow execution engine"),
    "web_search": ToolSpec("web_search", "arki_project.utils.web_search_pkg", "arki_project.utils.web_search", (), "web search utilities"),
    "plugin_system": ToolSpec("plugin_system", "arki_project.utils.plugin_system_pkg", "arki_project.utils.plugin_system", (), "plugin loading and execution"),
    "terminal_emulator": ToolSpec("terminal_emulator", "arki_project.utils.terminal_emulator_pkg", "arki_project.utils.terminal_emulator", (), "terminal emulation"),
    "campaign_orchestrator": ToolSpec("campaign_orchestrator", "arki_project.utils.campaign_orchestrator_pkg", "arki_project.utils.campaign_orchestrator", (), "campaign orchestration"),
    "data_analyzer": ToolSpec("data_analyzer", "arki_project.utils.data_analyzer_pkg", "arki_project.utils.data_analyzer", (), "data analysis utilities"),
    "openrouter_client": ToolSpec("openrouter_client", "arki_project.utils.openrouter_client_pkg", "arki_project.utils.openrouter_client", (), "OpenRouter API client"),
    "api_builder": ToolSpec("api_builder", "arki_project.infrastructure.api.api_builder_pkg", "arki_project.infrastructure.api.api_builder", ("APIBuilderAgent",), "API builder agent"),
    "stealth_worker": ToolSpec("stealth_worker", "arki_project.orchestration.workers.stealth_worker_pkg", "arki_project.orchestration.workers.stealth_worker", ("StealthWorker", "StealthConfig"), "browser automation worker"),
}


@lru_cache(maxsize=None)
def _import_first(paths: tuple[str, ...]) -> Any:
    last_error: Exception | None = None
    for path in paths:
        if not path:
            continue
        try:
            return importlib.import_module(path)
        except Exception as exc:  # optional/dependency-heavy modules may fail at import time
            last_error = exc
    if last_error:
        raise last_error
    raise ImportError("No module paths provided")


def list_tools() -> dict[str, ToolSpec]:
    return dict(_TOOL_SPECS)


def get_tool_module(name: str, *, prefer_legacy: bool = True) -> Any:
    spec = _TOOL_SPECS[name]
    order: Iterable[str | None]
    if prefer_legacy:
        order = (spec.legacy_module, spec.canonical_module)
    else:
        order = (spec.canonical_module, spec.legacy_module)
    return _import_first(tuple(p for p in order if p))


def get_tool_symbol(tool_name: str, symbol: str, *, default: Any = None) -> Any:
    try:
        module = get_tool_module(tool_name)
    except Exception:
        return default
    return getattr(module, symbol, default)


def has_tool(name: str) -> bool:
    try:
        get_tool_module(name)
        return True
    except Exception:
        return False


