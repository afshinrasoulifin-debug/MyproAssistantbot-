
from __future__ import annotations
"""
tg_bot/utils/v7_core.py — Centralized v7 Module Access
═══════════════════════════════════════════════════════════
SINGLE import point for all v7 modules. Uses singletons via lru_cache.
All handlers import from here instead of creating their own instances.

Usage:
    from arki_project.utils.v7_core import (
        get_memory, get_telemetry, get_prompt_engine,
        get_analyzer, get_transformer, with_v7,
    )
"""


import logging
import os
import aiofiles
import time
import functools
import threading

_singleton_lock = threading.Lock()
from typing import Any, Callable, Optional

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

# Maximum system prompt length to prevent token overflow
MAX_SYSTEM_PROMPT_LENGTH = 30000


# ── Singleton Getters (lru_cache ensures one instance across all handlers) ──

@functools.lru_cache(maxsize=1)
def get_memory() -> Any:
    """Get the shared MemoryStore singleton."""
    from arki_project.utils.memory_store import MemoryStore
    instance = MemoryStore()
    # Enable disk persistence
    instance._persist_path = "data/memory_store.json"
    instance._auto_persist = True
    _load_persisted_memory(instance)
    return instance


@functools.lru_cache(maxsize=1)
def get_telemetry() -> Any:
    """Get the shared TelemetryCollector singleton."""
    from arki_project.utils.telemetry_engine import TelemetryCollector
    return TelemetryCollector()


@functools.lru_cache(maxsize=1)
def get_prompt_engine() -> Any:
    """Get the shared PromptEngine singleton."""
    from arki_project.utils.advanced_prompt_engine import AdvancedPromptEngine
    return AdvancedPromptEngine()


@functools.lru_cache(maxsize=1)
def get_analyzer() -> Any:
    """Get the shared DataAnalyzer singleton."""
    from arki_project.utils.data_analyzer import DataAnalyzer
    return DataAnalyzer()


@functools.lru_cache(maxsize=1)
def get_transformer() -> Any:
    """Get the shared TextTransformer singleton."""
    from arki_project.utils.text_transform import TextTransformer
    return TextTransformer()


@functools.lru_cache(maxsize=1)
def get_web_recon() -> Any:
    """Get the shared WebRecon singleton."""
    from arki_project.utils.web_recon import WebRecon
    return WebRecon()


@functools.lru_cache(maxsize=1)
def get_multi_llm() -> Any:
    """Get the shared MultiLLMOrchestrator singleton."""
    from arki_project.utils.multi_llm_orchestrator import MultiLLMOrchestrator
    return MultiLLMOrchestrator()


@functools.lru_cache(maxsize=1)
def get_agent_executor() -> Any:
    """Get the agent_executor module for autonomous tool-calling agent."""
    from arki_project.utils import agent_executor as _agent_mod
    return _agent_mod


@functools.lru_cache(maxsize=1)
def get_workflow_engine() -> Any:
    """Get the shared WorkflowEngine singleton."""
    from arki_project.utils.workflow_engine import Workflow
    return Workflow(name="arki_main", description="Main Arki workflow engine")


@functools.lru_cache(maxsize=1)
def get_pipeline() -> Any:
    """Get the shared IntelligentPipeline singleton."""
    from arki_project.core.pipeline import IntelligentPipeline
    return IntelligentPipeline()


@functools.lru_cache(maxsize=1)
def get_reasoning_engine() -> Any:
    """Get the shared ReasoningEngine singleton."""
    from arki_project.core.reasoning import ReasoningEngine
    return ReasoningEngine()


@functools.lru_cache(maxsize=1)
def get_master_orchestrator() -> Any:
    """Get the shared MasterOrchestrator singleton."""
    from arki_project.utils.master_orchestrator import MasterOrchestrator
    return MasterOrchestrator()


@functools.lru_cache(maxsize=1)
def get_autorun_engine() -> Any:
    """Get the shared AutoRunEngine singleton."""
    from arki_project.core.autorun import AutoRunEngine
    return AutoRunEngine()


@functools.lru_cache(maxsize=1)
def get_web_automation() -> Any:
    """Get the shared WebAutomation via stealth_worker fallback."""
    try:
        from arki_project.orchestration.workers.stealth_worker import StealthWorker
        return StealthWorker()
    except ImportError:
        logger.debug("WebAutomation: stealth_worker not available")
        return None


@functools.lru_cache(maxsize=1)
def get_marketing_engine() -> Any:
    """Get the shared MarketingEngine singleton."""
    from arki_project.utils.marketing_engine import MarketingEngine
    return MarketingEngine()


# ── Memory Persistence ──

def _load_persisted_memory(memory_store: Any) -> None:
    """Load persisted memory from disk on startup."""
    import json
    path = getattr(memory_store, "_persist_path", None)
    if not path:
        return
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                raw = f.read()
                data = json.loads(raw)
            if hasattr(memory_store, "load_from_dict"):
                memory_store.load_from_dict(data)
            elif hasattr(memory_store, "_store") and isinstance(data, dict):
                memory_store._store = data
            logger.info("Memory loaded from %s (%d entries)", path, len(data))
    except Exception as e:
        logger.warning("Failed to load persisted memory: %s", e)


async def persist_memory() -> None:
    """Persist memory store to disk. Called periodically or on shutdown."""
    import json
    mem = get_memory()
    path = getattr(mem, "_persist_path", "data/memory_store.json")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {}
        if hasattr(mem, "to_dict"):
            data = mem.to_dict()
        elif hasattr(mem, "_store"):
            data = mem._store
        async with aiofiles.open(path, "w") as f:
            await f.write(json.dumps(data, ensure_ascii=False, default=str))
        logger.debug("Memory persisted to %s", path)
    except Exception as e:
        logger.warning("Memory persist failed: %s", e)


# ── Dynamic Reasoning Mode ──

def get_reasoning_mode(text: str, complexity: str = "auto") -> Any:
    """Choose reasoning mode dynamically based on input complexity."""
    from arki_project.utils.advanced_prompt_engine import ReasoningMode

    if complexity != "auto":
        mode_map = {
            "trivial": ReasoningMode.DIRECT,
            "simple": ReasoningMode.DIRECT,
            "moderate": ReasoningMode.CHAIN_OF_THOUGHT,
            "complex": ReasoningMode.REACT,
            "expert": ReasoningMode.TREE_OF_THOUGHT,
        }
        return mode_map.get(complexity, ReasoningMode.CHAIN_OF_THOUGHT)

    # Auto-detect: short/simple → DIRECT, medium → COT, long/complex → REACT
    word_count = len(text.split())
    has_comparison = any(w in text.lower() for w in ["مقایسه", "compare", "تفاوت", "بهتر", "vs"])
    has_analysis = any(w in text.lower() for w in ["تحلیل", "analyze", "بررسی", "ارزیابی", "strategy"])
    has_multi_step = any(w in text.lower() for w in ["مرحله", "step", "plan", "workflow", "pipeline"])

    if has_multi_step or (has_analysis and word_count > 50):
        return ReasoningMode.TREE_OF_THOUGHT
    elif has_comparison or has_analysis or word_count > 30:
        return ReasoningMode.REACT
    elif word_count > 15:
        return ReasoningMode.CHAIN_OF_THOUGHT
    else:
        return ReasoningMode.DIRECT


# ── Enhanced System Prompt Builder ──

def enhance_system_prompt(system_text: str, user_text: str = "", user_id: str = "") -> str:
    """
    Enhance system prompt with RAG context + prompt engineering.
    Used by all handlers before AI calls.
    """
    try:
        memory = get_memory()
        engine = get_prompt_engine()

        # Build RAG context from user memory
        rag_context = ""
        if user_id:
            try:
                rag_context = memory.build_rag_context(
                    user_text, user_id=user_id, max_tokens=16384
                )
            except Exception as e:
                logger.debug("Suppressed: %s", e)

        # Enhance prompt
        enhanced = system_text
        try:
            from arki_project.utils.advanced_prompt_engine import PromptConfig
            mode = get_reasoning_mode(user_text)
            config = PromptConfig(reasoning_mode=mode)
            result = engine.build(user_text, config=config, rag_context=rag_context)
            if hasattr(result, "system_prompt") and result.system_prompt:
                enhanced += f"\n\n[ENHANCED CONTEXT]\n{result.system_prompt}\n[/ENHANCED CONTEXT]"
        except Exception as e:
            logger.debug("Suppressed: %s", e)

        if rag_context:
            enhanced += f"\n\n[USER MEMORY]\n{rag_context}\n[/USER MEMORY]"

        # Guard against prompt inflation
        if len(enhanced) > MAX_SYSTEM_PROMPT_LENGTH:
            enhanced = enhanced[:MAX_SYSTEM_PROMPT_LENGTH] + "\n[TRUNCATED]"
        return enhanced
    except Exception:
        return system_text


# ── Store Result Helper ──

def store_result(
    user_id: int,
    query: str,
    answer: str,
    cmd: str,
    duration_s: float = 0.0,
    success: bool = True,
    metadata: Optional[dict] = None,
) -> None:
    """Store AI result in shared memory and record telemetry."""
    try:
        from arki_project.utils.memory_store import MemoryType
        mem = get_memory()
        mem.store(
            content=f"Q: {query[:300]}\nA: {answer[:500]}",
            mem_type=MemoryType.CONVERSATION,
            user_id=str(user_id),
            tags=[cmd],
        )
    except Exception as e:
        logger.warning("store_result memory error for %s: %s", cmd, e)

    try:
        tel = get_telemetry()
        tel.record(cmd, duration_s=duration_s, success=success, metadata=metadata or {})
    except Exception as e:
        logger.warning("store_result telemetry error for %s: %s", cmd, e)


# ── @with_v7 Decorator ──

def with_v7(cmd: str) -> Any:
    """
    Decorator that adds RAG + memory + telemetry to any handler function.

    The decorated function receives extra kwargs:
        - rag_context: str  — retrieved memory for this user+query
        - v7_system: callable(str) -> str  — enhances a system prompt

    After execution, stores result and records timing automatically.

    Usage:
        @with_v7("search")
        async def cmd_search(message, *args, rag_context="", v7_system=None, **kwargs):
            system = v7_system("You are a search expert.")
            result = await ai_client.ask_raw(...)
            return result  # stored automatically
    """
    def decorator(func: Callable) -> Any:
        @functools.wraps(func)
        async def wrapper(message: str, *args, **kwargs) -> Any:
            uid = str(message.from_user.id) if message.from_user else "0"
            text = message.text or ""

            # Build RAG context
            rag_ctx = ""
            try:
                rag_ctx = get_memory().build_rag_context(text, user_id=uid, max_tokens=16384)
            except Exception as e:
                logger.debug("Suppressed: %s", e)

            # System prompt enhancer
            def v7_sys(system_text: str) -> str:
                return enhance_system_prompt(system_text, user_text=text, user_id=uid)

            # Inject v7 context into kwargs
            kwargs["rag_context"] = rag_ctx
            kwargs["v7_system"] = v7_sys

            # Execute with timing
            t0 = time.time()
            try:
                result = await func(message, *args, **kwargs)
                duration = time.time() - t0

                # Store result
                result_text = str(result)[:500] if result else ""
                store_result(
                    user_id=int(uid) if uid.isdigit() else 0,
                    query=text[:300],
                    answer=result_text,
                    cmd=cmd,
                    duration_s=duration,
                    success=True,
                )
                return result
            except Exception as exc:
                duration = time.time() - t0
                store_result(
                    user_id=int(uid) if uid.isdigit() else 0,
                    query=text[:300],
                    answer=f"ERROR: {exc}",
                    cmd=cmd,
                    duration_s=duration,
                    success=False,
                )
                raise

        return wrapper
    return decorator


# ── Timed AI Call Helper ──

async def timed_ai_call(ai_func: Any, *args, cmd: str = "unknown", user_id: int = 0, query: str = "", **kwargs) -> Any:
    """
    Wrap any ai_client.ask() or ask_raw() call with timing + memory storage.

    Usage:
        result = await timed_ai_call(
            ai_client.ask_raw, messages=msgs, model_key=mk,
            cmd="search", user_id=uid, query=text
        )
    """
    t0 = time.time()
    try:
        result = await ai_func(*args, **kwargs)
        duration = time.time() - t0
        store_result(user_id, query, str(result)[:500] if result else "", cmd, duration, True)
        return result
    except Exception as exc:
        duration = time.time() - t0
        store_result(user_id, query, f"ERROR: {exc}", cmd, duration, False)
        raise


