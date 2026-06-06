
from __future__ import annotations
"""
tg_bot/core/ai_middleware.py
────────────────────────────
🧠 AI Middleware — Transparently enhances ALL AI calls with v7 modules.

Instead of modifying every handler, this middleware wraps the AIClient
to automatically apply:
  ✅ Prompt enhancement (AdvancedPromptEngine)
  ✅ Memory context injection (MemoryStore)
  ✅ AutoTune temperature (AutoTune)
  ✅ Semantic memory storage (post-call)
  ✅ Telemetry recording (TelemetryEngine)

This means EVERY handler that calls ai_client.ask() or ai_client.ask_raw()
automatically benefits from all 22 v7 modules — zero handler changes needed.

Architecture:
  Original: handler → ai_client.ask_raw() → provider
  Enhanced: handler → ai_middleware.ask_raw() → v7_enhance → ai_client.ask_raw() → provider → v7_store

Reference: Brown et al. (2020) "Language Models are Few-Shot Learners" — prompt engineering
"""


import functools
import logging
import time
from typing import Any, Dict

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config
    from arki_project.utils.titanium.crypto import secure_hex
except ImportError:
    pass
logger = logging.getLogger(__name__)

_bridge = None
_original_ask = None
_original_ask_raw = None
_is_installed = False


def _get_bridge() -> Any:
    """Lazy-load the module bridge."""
    global _bridge
    if _bridge is None:
        try:
            from arki_project.core.module_bridge import bridge
            _bridge = bridge
            logger.info("✅ AI Middleware: ModuleBridge connected")
        except Exception as exc:
            logger.warning("AI Middleware: ModuleBridge unavailable: %s", exc)
    return _bridge


def install_middleware(ai_client: Any) -> bool:
    """
    Install v7 middleware on an AIClient instance.
    
    This wraps ask() and ask_raw() to transparently add:
    - Prompt enhancement
    - Memory context
    - AutoTune
    - Post-call memory storage
    - Telemetry
    
    Returns True if installed successfully.
    """
    global _original_ask, _original_ask_raw, _is_installed
    
    if _is_installed:
        logger.info("AI Middleware already installed")
        return True
    
    try:
        # Save original methods
        _original_ask = ai_client.ask
        _original_ask_raw = ai_client.ask_raw
        
        # Install enhanced versions
        ai_client.ask = _make_enhanced_ask(ai_client)
        ai_client.ask_raw = _make_enhanced_ask_raw(ai_client)
        
        _is_installed = True
        logger.info("✅ AI Middleware installed — all AI calls now v7-enhanced")
        return True
        
    except Exception as exc:
        logger.error("Failed to install AI Middleware: %s", exc)
        return False


def uninstall_middleware(ai_client: Any) -> None:
    """Remove middleware, restore original methods."""
    global _original_ask, _original_ask_raw, _is_installed
    
    if not _is_installed:
        return
    
    if _original_ask:
        ai_client.ask = _original_ask
    if _original_ask_raw:
        ai_client.ask_raw = _original_ask_raw
    
    _is_installed = False
    logger.info("AI Middleware uninstalled")


def _make_enhanced_ask(ai_client: Any) -> Any:
    """Create an enhanced version of ai_client.ask()."""
    original = _original_ask
    
    @functools.wraps(original)
    async def enhanced_ask(
        user_id: int,
        text: str,
        model_key: str = "auto",
        system_prompt: str = "",
        temperature: float = 0.85,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str:
        start = time.time()
        bridge = _get_bridge()
        
        enhanced_system = system_prompt
        enhanced_temp = temperature
        
        if bridge:
            try:
                # 1. Classify the request
                category, complexity, confidence = await bridge.classify(
                    user_id, text,
                )
            except Exception:
                category, complexity, confidence = "chat", 1, 0.5
            
            try:
                # 2. Enhance system prompt
                enhanced_system = bridge.enhance_prompt(
                    system_prompt,
                    category=category,
                    style="professional",
                )
            except Exception as e:
                logger.debug("Suppressed: %s", e)
            
            try:
                # 3. Inject memory context
                mem_ctx = bridge.build_memory_context(user_id, text)
                if mem_ctx:
                    enhanced_system = f"{enhanced_system}\n\n{mem_ctx}"
            except Exception as e:
                logger.debug("Suppressed: %s", e)
            
            try:
                # 4. Add reasoning for complex tasks (v10: passes text for smarter selection)
                if complexity >= 3:
                    strategy = _select_strategy(category, complexity, text)
                    reasoning = bridge.build_reasoning_prompt(
                        text, strategy=strategy,
                    )
                    if reasoning:
                        enhanced_system = (
                            f"{enhanced_system}\n\n"
                            f"[REASONING]\n{reasoning}\n[/REASONING]"
                        )
            except Exception as e:
                logger.debug("Suppressed: %s", e)
            
            try:
                # 5. AutoTune temperature
                tuned = bridge.autotune_params(user_id, text)
                if tuned:
                    enhanced_temp = tuned.get("temperature", temperature)
            except Exception as e:
                logger.debug("Suppressed: %s", e)
        
        # v10: Use smart temperature when no autotune result available
        if enhanced_temp == temperature:
            try:
                from arki_project.utils.ai_client import smart_select_temperature
                enhanced_temp = smart_select_temperature(text, category if 'category' in dir() else "chat")
            except ImportError:
                pass

        # Call original
        result = await original(
            user_id=user_id,
            text=text,
            model_key=model_key,
            system_prompt=enhanced_system,
            temperature=enhanced_temp,
            max_tokens=max_tokens,
            **kwargs,
        )
        
        elapsed = time.time() - start

        # v10: Post-response quality check (non-blocking, just logs)
        try:
            from arki_project.utils.quality_gate import get_quality_gate
            from arki_project.utils.hallucination_detector import get_hallucination_detector
            qg = get_quality_gate()
            hd = get_hallucination_detector()
            q_report = qg.evaluate(result, text)
            h_report = hd.check(result, context=text)
            if not q_report.passed:
                logger.warning(
                    "AI Middleware: quality gate FAILED (score=%.2f) for user=%d",
                    q_report.overall_score, user_id,
                )
            if h_report.is_suspicious:
                logger.warning(
                    "AI Middleware: hallucination detected (score=%.2f) for user=%d",
                    h_report.score, user_id,
                )
        except Exception as _e:
            logger.debug("Suppressed: %s", _e)  # v10.1: no longer silent

        if bridge:
            try:
                # 6. Store in semantic memory
                bridge.remember(
                    user_id,
                    f"Q: {text[:200]}\nA: {result[:200]}",
                    metadata={
                        "model": model_key,
                        "category": category if 'category' in dir() else "unknown",
                    },
                )
            except Exception as e:
                logger.debug("Suppressed: %s", e)
            
            try:
                # 7. Telemetry
                bridge.record_event(
                    module="ai_middleware",
                    duration_s=elapsed,
                    success=True,
                    metadata={"model": model_key},
                )
            except Exception as e:
                logger.debug("Suppressed: %s", e)
        
        return result
    
    return enhanced_ask


def _make_enhanced_ask_raw(ai_client: Any) -> Any:
    """Create an enhanced version of ai_client.ask_raw()."""
    original = _original_ask_raw
    
    @functools.wraps(original)
    async def enhanced_ask_raw(
        messages: list,
        model_key: str = "auto",
        temperature: float = 0.85,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str:
        start = time.time()
        bridge = _get_bridge()
        
        enhanced_messages = list(messages)  # shallow copy
        enhanced_temp = temperature
        
        if bridge and enhanced_messages:
            # Extract system prompt and user text for enhancement
            system_msg = None
            user_text = ""
            
            for msg in enhanced_messages:
                if msg.get("role") == "system":
                    system_msg = msg
                elif msg.get("role") == "user":
                    user_text = msg.get("content", "")
            
            if system_msg:
                try:
                    # Enhance system prompt
                    original_content = system_msg["content"]
                    enhanced_content = bridge.enhance_prompt(
                        original_content, category="general",
                    )
                    # Create new message list with enhanced system prompt
                    enhanced_messages = []
                    for msg in messages:
                        if msg.get("role") == "system":
                            enhanced_messages.append({
                                "role": "system",
                                "content": enhanced_content,
                            })
                        else:
                            enhanced_messages.append(msg)
                except Exception as e:
                    logger.debug("Suppressed: %s", e)
            
            if user_text:
                try:
                    # AutoTune
                    tuned = bridge.autotune_params(0, user_text)
                    if tuned:
                        enhanced_temp = tuned.get("temperature", temperature)
                except Exception as e:
                    logger.debug("Suppressed: %s", e)
        
        # Call original
        result = await original(
            messages=enhanced_messages,
            model_key=model_key,
            temperature=enhanced_temp,
            max_tokens=max_tokens,
            **kwargs,
        )
        
        elapsed = time.time() - start
        
        if bridge:
            try:
                bridge.record_event(
                    module="ai_middleware_raw",
                    duration_s=elapsed,
                    success=True,
                    metadata={"model": model_key},
                )
            except Exception as e:
                logger.debug("Suppressed: %s", e)
        
        return result
    
    return enhanced_ask_raw


def _select_strategy(category: str, complexity: int, text: str = "") -> str:
    """Select reasoning strategy — v10: delegates to ReasoningEngine."""
    try:
        from arki_project.core.reasoning import ReasoningEngine
        engine = ReasoningEngine()
        return engine.auto_select_strategy(text, category=category, complexity=complexity)
    except Exception as _e:
        logger.debug("Suppressed: %s", _e)  # v10.1: no longer silent

    # Fallback to hardcoded logic
    if complexity >= 5:
        return "tree_of_thought"
    if complexity >= 4:
        return "self_refine"
    if category in ("code", "math", "analysis"):
        return "chain_of_thought"
    if category in ("research", "search"):
        return "react"
    return "chain_of_thought"


def get_middleware_stats() -> Dict[str, Any]:
    """Get middleware status and stats."""
    bridge = _get_bridge()
    return {
        "installed": _is_installed,
        "bridge_available": bridge is not None,
        "original_ask_saved": _original_ask is not None,
        "original_ask_raw_saved": _original_ask_raw is not None,
    }


