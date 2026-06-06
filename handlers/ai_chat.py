
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
tg_bot/handlers/ai_chat.py
──────────────────────────
Core chat handler:

  • /new — clear conversation history
  • Catch-all text handler — routes plain text to AI with user's
    chosen model, persona, and AutoTune settings.
  • Smart intent detection — auto-routes search/image requests.
  • AI response post-processing — auto-generates images when AI
    outputs /image commands in its response text.

⚠️ This router MUST be registered LAST because the text handler
matches all non-command text messages.
"""


import logging
import re

from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from arki_project.config import Settings
from arki_project.utils.ai_client import AIClient

# v26.0: Quality Engine
try:
    from arki_project.utils.smart_router import get_smart_router
    from arki_project.utils.consensus_engine import get_consensus_engine, ConsensusStrategy
    from arki_project.utils.adaptive_prompt import get_adaptive_prompt
    from arki_project.utils.performance_analytics import get_analytics
    _HAS_QUALITY_ENGINE = True
except ImportError:
    _HAS_QUALITY_ENGINE = False
from arki_project.utils.image_gen import generate_image
from arki_project.utils.models_registry import (
    MODELS,
    PERSONAS,
    split_for_telegram,
    user_friendly_error,
    working_model_key,
)
from arki_project.utils.web_search import search_with_fallback
from arki_project.utils.safe_send import safe_reply
from arki_project.utils.context_manager import get_context_manager
from arki_project.utils.ai_output_validator import get_output_validator
from arki_project.utils.hallucination_detector import get_hallucination_detector
from arki_project.utils.v7_core import (
    get_memory, get_prompt_engine,
    get_reasoning_mode, get_pipeline,
)
from arki_project.autonomous_core.thinking_agent import ThinkingAgentPro
from arki_project.utils.memory_store import MemoryType
from arki_project.utils.advanced_prompt_engine import PromptConfig

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config 
except ImportError:
    pass
# v10.2: Wire previously orphan modules
try:
    _STREAMING_AVAILABLE = True
except ImportError:
    _STREAMING_AVAILABLE = False
try:
    _RESPONSE_TYPES_AVAILABLE = True
except ImportError:
    _RESPONSE_TYPES_AVAILABLE = False

# ── Infrastructure access (injected by middleware) ──
# Access via data["infra_registry"], data["infra_event_bus"], data["infra_config"]


logger = logging.getLogger(__name__)
router = Router(name="ai_chat")

# ─── Intent detection patterns (expanded) ───

_SEARCH_PATTERNS = re.compile(
    r"(سرچ|جستجو|اینترنت|search|بگرد|خبر|اخبار|آخرین|"
    r"امروز|الان چی|قیمت\s+\S+|نرخ\s+\S+|"
    r"بری اینترنت|از نت|از اینترنت|وب\s*سرچ|google|گوگل)",
    re.IGNORECASE,
)

# Expanded image patterns — includes لوگو, logo, طراحی, design, بنر, banner,
# پوستر, poster, آیکون, icon, render, کاور, cover, والپیپر, wallpaper
_IMAGE_PATTERNS = re.compile(
    r"("
    # Persian: make/draw/create image
    r"عکس\s*(بساز|بکش|تولید|بزن|درست\s*کن)|"
    r"تصویر\s*(بساز|بکش|تولید|بزن|درست\s*کن)|"
    r"(بساز|بکش|بزن|درست\s*کن|تولید\s*کن)\s*(یه|یک|)\s*(عکس|تصویر|لوگو|بنر|پوستر|آیکون|کاور)|"
    # Persian: logo, banner, poster, icon, cover, wallpaper + make
    r"لوگو\s*(بساز|بکش|بزن|درست\s*کن|تولید|طراحی)|"
    r"(بساز|بکش|بزن|طراحی\s*کن)\s*.*\s*لوگو|"
    r"بنر\s*(بساز|بکش|بزن|درست\s*کن)|"
    r"پوستر\s*(بساز|بکش|بزن|درست\s*کن)|"
    r"آیکون\s*(بساز|بکش|بزن|درست\s*کن)|"
    r"کاور\s*(بساز|بکش|بزن|درست\s*کن)|"
    r"والپیپر\s*(بساز|بکش|بزن|درست\s*کن)|"
    r"نقاشی\s*(بکش|بساز|بزن)|"
    # Persian: design/create
    r"طراحی\s*(کن|بکن)\s*(یه|یک|)\s*(لوگو|بنر|پوستر|عکس|تصویر|آیکون)|"
    # English
    r"draw\s|generate\s+(an?\s+)?image|create\s+(an?\s+)?image|"
    r"make\s+(an?\s+)?(image|logo|banner|poster|icon|cover|design)|"
    r"design\s+(a\s+)?logo|create\s+(a\s+)?logo|generate\s+(a\s+)?logo|"
    r"render\s|illustrate\s"
    r")",
    re.IGNORECASE,
)

# Pattern to detect /image commands in AI responses (for auto-execution)
_IMAGE_CMD_RE = re.compile(r"^/image\s+(.+)$", re.MULTILINE)

# Max images to auto-generate from AI response
_MAX_AUTO_IMAGES = 3


def _extract_search_query(text: str) -> str:
    """Try to extract the actual search topic from a natural request."""
    for pat in [
        r"(میخوام|می‌خوام|لطفا|لطفاً)\s*(بری|از)\s*(اینترنت|نت)\s*(و|)\s*",
        r"(سرچ|جستجو)\s*(کن|بکن|بزن)\s*",
        r"(راجب|درباره|درمورد|در مورد)\s*",
        r"(بگرد|بگرد ببین)\s*",
        r"(خبر|اخبار)\s*(بیار|بده|پیدا کن)\s*",
    ]:
        text = re.sub(pat, "", text, flags=re.IGNORECASE).strip()
    return text.strip() if text.strip() else ""


def _extract_image_prompt(text: str) -> str:
    """
    Extract the image prompt from a natural language request.
    
    Instead of stripping all the keywords, we pass the full context
    to generate_image() which has its own smart prompt enhancer.
    We only strip trivial action verbs.
    """
    # Remove just the action words but keep the subject/context
    prompt = re.sub(
        r"(بساز|بکش|بزن|درست\s*کن|تولید\s*کن|طراحی\s*کن)\s*(یه|یک|)?\s*",
        "", text, flags=re.IGNORECASE,
    ).strip()
    # Remove trailing/leading punctuation
    prompt = prompt.strip("،. !؟?")
    return prompt if prompt else text


async def _safe_delete(msg: Message) -> None:
    """Delete a message, ignoring errors if already deleted."""
    try:
        await msg.delete()
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)


async def _generate_and_send_image(
    message: Message, prompt: str, caption: str | None = None,
) -> bool:
    """Generate an image and send it. Returns True on success."""
    try:
        image_bytes = await generate_image(prompt)
        photo = BufferedInputFile(image_bytes, filename="arki.png")
        cap = caption or f"🎨 _{prompt[:100]}_"
        try:
            await message.answer_photo(photo=photo, caption=cap, parse_mode="Markdown")
        except HandlerError:
            await message.answer_photo(photo=photo, caption=cap)
        return True
    except HandlerError as exc:
        logger.warning("Image generation failed for prompt '%s': %s", prompt[:60], exc)
        return False


async def _process_ai_response_images(
    message: Message, answer: str,
) -> str:
    """
    Detect /image commands in AI response text, auto-generate images,
    and return the cleaned text (with /image lines removed).
    """
    matches = _IMAGE_CMD_RE.findall(answer)
    if not matches:
        return answer

    # Limit to max auto images
    prompts = [m.strip() for m in matches[:_MAX_AUTO_IMAGES] if m.strip()]
    if not prompts:
        return answer

    # Notify user that images are being generated
    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO,
    )

    # Generate images (in parallel for speed, but limit concurrency)
    for i, prompt in enumerate(prompts):
        caption = f"🎨 *({i+1}/{len(prompts)})* _{prompt[:80]}_"
        success = await _generate_and_send_image(message, prompt, caption)
        if not success:
            try:
                await safe_reply(message, f"⚠️ تولید تصویر {i+1} ناموفق بود. "
                    f"می‌تونی دستی امتحان کنی:\n`/image {prompt[:100]}`")
            except HandlerError as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(
                    f"⚠️ تولید تصویر {i+1} ناموفق بود."
                )

    # Remove /image lines from the text response
    cleaned = _IMAGE_CMD_RE.sub("", answer).strip()
    # Clean up excessive blank lines left after removal
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


# ═══════════ /new — clear history ═══════════

@router.message(Command("new"))
async def cmd_new(message: Message, ai_client: AIClient) -> None:
    user_id = message.from_user.id  # type: ignore[union-attr]
    await ai_client.clear_history(user_id)
    await message.answer("🗑 حافظه پاک شد! ✨")


# ═══════════ Catch-all text → AI (with smart routing) ═══════════

@router.message()
async def handle_text(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    if not message.text:
        return
    text = message.text.strip()
    if not text:
        return

    # Input length guard — prevent abuse with extremely long messages
    MAX_INPUT_LENGTH = 100000
    if len(text) > MAX_INPUT_LENGTH:
        text = text[:MAX_INPUT_LENGTH]
        await safe_reply(message, f"⚠️ پیام خیلی طولانی بود ({len(message.text)} کاراکتر). فقط اول {MAX_INPUT_LENGTH} کاراکتر پردازش شد.")

    user_id = message.from_user.id  # type: ignore[union-attr]

    # ── Smart intent detection: Auto-search ──
    if _SEARCH_PATTERNS.search(text) and settings.ai_api_key:
        query = _extract_search_query(text) or text
        await message.bot.send_chat_action(  # type: ignore[union-attr]
            chat_id=message.chat.id, action=ChatAction.TYPING,
        )
        status = await message.answer("🔍 دارم اینترنت رو سرچ می‌کنم...")
        try:
            answer = await search_with_fallback(
                query,
                settings.ai_api_key,
                model=settings.ai_model,
                base_url=settings.ai_base_url,
            )
            await _safe_delete(status)
            for chunk in split_for_telegram(answer):
                try:
                    await safe_reply(message, chunk)
                except HandlerError:
                    await message.answer(chunk)
            return
        except HandlerError as exc:
            logger.warning("Auto-search failed, falling back to AI: %s", exc)
            await _safe_delete(status)
            # Fall through to regular AI chat.

    # ── Smart intent detection: Auto-image ──
    if _IMAGE_PATTERNS.search(text):
        prompt = _extract_image_prompt(text)
        if prompt:
            await message.bot.send_chat_action(  # type: ignore[union-attr]
                chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO,
            )
            success = await _generate_and_send_image(message, prompt)
            if success:
                return
            # Fall through to regular AI chat if image gen failed.
            logger.warning("Auto-image failed, falling through to AI chat")

    # ── Check APEX status from Extra module ──
    from arki_project.extra.router import get_apex_prompt, apply_stm_to_response, _stm_users
    apex_prompt = get_apex_prompt(user_id)

    # ═══════════════════════════════════════════════════════════════
    # APEX ACTIVE → Try APEX first, fallback to native AI
    # ═══════════════════════════════════════════════════════════════
    if apex_prompt:
        import os
        from arki_project.extra import bridge

        _apex_handled = False

        # Only try APEX if server is available
        if await bridge.is_server_running():
            # v25.0 AUTONOMOUS: Resolve key from all sources
            or_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
            if not or_key:
                try:
                    from arki_project.utils.free_access_router import get_free_router
                    _fr = get_free_router()
                    _pk = _fr._provisioned_keys.get("openrouter_free", [])
                    or_key = _pk[0] if _pk else ""
                except HandlerError:
                    or_key = ""
                if not or_key:
                    or_key = settings.ai_api_key or ""
                logger.info("APEX AUTONOMOUS: using %s", "provisioned key" if or_key else "free tier")

            await message.bot.send_chat_action(
                chat_id=message.chat.id, action=ChatAction.TYPING,
            )

            stm = _stm_users.get(user_id, [])
            result = await bridge.chat_completion(
                messages=[{"role": "user", "content": text}],
                model="google/gemini-2.5-pro",
                openrouter_api_key=or_key,
                apex=True,
                autotune=True,
                parseltongue=False,
                stm_modules=stm if stm else None,
            )

            if result.success:
                data = result.data
                answer = ""
                if "choices" in data and data["choices"]:
                    answer = data["choices"][0].get("message", {}).get("content", "")
                elif "content" in data:
                    answer = data["content"]

                if answer.strip():
                    answer = await _process_ai_response_images(message, answer)
                    if answer.strip():
                        for chunk in split_for_telegram(answer):
                            try:
                                await safe_reply(message, chunk)
                            except HandlerError as exc:
                                logger.error("Error in handler: %s", exc)
                                await message.answer(chunk)
                    _apex_handled = True
                else:
                    logger.info("APEX: APEX returned empty, falling through to native AI")
            else:
                logger.warning("APEX: APEX failed (%s), falling through to native AI", result.error)
        else:
            logger.info("APEX: APEX server not available, using native AI")

        if _apex_handled:
            return
        # Fall through to native AI path below

    # ═══════════════════════════════════════════════════════════════
    # APEX / OpenRouter model selected → Try bridge, fallback to native
    # ═══════════════════════════════════════════════════════════════
    cfg = await ai_client.get_user_config(user_id)
    selected_model_info = MODELS.get(cfg["model"])
    if selected_model_info and selected_model_info.provider == "openrouter":
        import os
        from arki_project.extra import bridge

        _or_handled = False
        if await bridge.is_server_running():
            # v25.0 AUTONOMOUS: Resolve key from all sources
            or_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
            if not or_key:
                try:
                    from arki_project.utils.free_access_router import get_free_router
                    _fr = get_free_router()
                    _pk = _fr._provisioned_keys.get("openrouter_free", [])
                    or_key = _pk[0] if _pk else ""
                except HandlerError:
                    or_key = ""
                if not or_key:
                    or_key = settings.ai_api_key or ""
                logger.info("OpenRouter AUTONOMOUS: using %s", "provisioned key" if or_key else "free tier")

            await message.bot.send_chat_action(
                chat_id=message.chat.id, action=ChatAction.TYPING,
            )

            stm = _stm_users.get(user_id, [])
            result = await bridge.chat_completion(
                messages=[{"role": "user", "content": text}],
                model=selected_model_info.id,
                openrouter_api_key=or_key,
                apex=False,
                autotune=True,
                parseltongue=False,
                stm_modules=stm if stm else None,
            )

            if result.success:
                data = result.data
                answer = ""
                if "choices" in data and data["choices"]:
                    answer = data["choices"][0].get("message", {}).get("content", "")
                elif "content" in data:
                    answer = data["content"]

                if answer.strip():
                    answer = await _process_ai_response_images(message, answer)
                    if answer.strip():
                        for chunk in split_for_telegram(answer):
                            try:
                                await safe_reply(message, chunk)
                            except HandlerError as exc:
                                logger.error("Error in handler: %s", exc)
                                await message.answer(chunk)
                    _or_handled = True
                else:
                    logger.info("OpenRouter: empty response, falling through to native AI")
            else:
                logger.warning("OpenRouter: bridge failed (%s), falling through to native AI", result.error)
        else:
            logger.info("OpenRouter: APEX not available, falling through to native AI")

        if _or_handled:
            return
        # Fall through to native AI

    # ═══════════════════════════════════════════════════════════════
    # Regular AI chat (Gemini / Groq — APEX OFF)
    # ═══════════════════════════════════════════════════════════════
    mk = working_model_key(
        cfg["model"], settings.ai_api_key, settings.groq_api_key,
    )
    if mk is None:
        mk = "gemini-pro"  # v9.7.1: Always have a fallback

    persona = PERSONAS.get(cfg["persona"], PERSONAS["assistant"])

    # System prompt with image generation awareness.
    sys_prompt = (
        f"{persona.system_prompt}\n\n"
        "You are Arki Engine — a powerful AI assistant with built-in tools.\n\n"
        "IMPORTANT — IMAGE GENERATION:\n"
        "When the user asks you to create/make/draw/design an image, logo, "
        "banner, poster, icon, or any visual content, you MUST include a line "
        "starting with `/image ` followed by a detailed English prompt.\n"
        "Example: `/image A sleek modern logo for a candle brand...`\n"
        "The system will automatically generate and send the image.\n"
        "You can include up to 3 `/image` lines for variations.\n"
        "Each /image line must be on its OWN line.\n\n"
        "APEX FEATURE:\n"
        "This bot has a APEX engine with 59 AI models. Users can activate "
        "APEX via /apex command. When active, all regular messages will "
        "be processed through APEX pipeline (bypassing filters). "
        "If the user asks about APEX status, tell them to use /apex.\n"
        "Other APEX commands: /extra /race /consortium /chat /parseltongue "
        "/autotunepro /stm /libertas /classify /feedback /g0dstatus\n\n"
        "OTHER COMMANDS (tell the user about these, don't execute them):\n"
        "/search — web search | /deep — deep research\n"
        "/voice — text-to-speech (9 voices)\n"
        "/translate /summarize /code /polish /explain /math /brainstorm\n"
        "/create — generate files (PDF, code, etc.)\n"
        "/compare — compare 2 AI models | /consensus — multi-model\n"
        "/model — choose from 19 AI models | /persona — 10 personalities\n"
        "/poster — 4 sale poster templates | /photopro — product photos\n"
        "/listing — marketplace listings (Etsy/Tori.fi/Instagram)\n"
        "/content — all-in-one content generator\n"
    )

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )

    # 1. Prepare steps for ThinkingAgentPro
    chat_steps = ["تحلیل ارکستراتور", "بازیابی حافظه (RAG)", "پردازش نهایی و پاسخ"]
    status = await safe_reply(message, "🧠 *در حال تفکر...*")
    if not status: return

    try:
        async with ThinkingAgentPro(bot=message.bot, chat_id=message.chat.id, initial_message=status, total_steps=len(chat_steps)) as agent:
            await agent.set_total_steps(len(chat_steps), chat_steps)
            
            # ── v9: IntelligentPipeline — classify → context → reason → execute ──
            import time as _t
            _v9_t0 = _t.time()
            _pipeline_result = None

            # Step 1: Orchestrator
            await agent.start_step(0)
            await agent.update_thought("در حال برنامه‌ریزی پاسخ با ارکستراتور...", active_model=mk)
            try:
                pipeline = get_pipeline()
                # Fetch RAG memory for pipeline context
                _memory_results = []
                try:
                    mem = get_memory()
                    _search_results = mem.search(text, limit=5, user_id=str(user_id))
                    if _search_results:
                        _memory_results = [
                            {"content": sr.memory.content, "score": sr.score,
                             "timestamp": sr.memory.created_at}
                            for sr in _search_results
                        ]
                except HandlerError as _mem_err:
                    logger.warning("v9 pipeline memory recall: %s", _mem_err)

                _pipeline_result = await pipeline.process(
                    user_id=user_id,
                    text=text,
                    memory_results=_memory_results,
                )

                # Enrich system prompt with pipeline intelligence
                if _pipeline_result.enriched_prompt:
                    sys_prompt += f"\n\n[PIPELINE INTELLIGENCE — {_pipeline_result.category.value.upper()}]\n"
                    sys_prompt += f"Strategy: {_pipeline_result.reasoning_strategy.value}\n"
                    sys_prompt += f"Modules: {', '.join(_pipeline_result.modules_used)}\n"
                    sys_prompt += _pipeline_result.enriched_prompt
                    sys_prompt += "\n[/PIPELINE INTELLIGENCE]"
                
                await agent.update_thought(f"استراتژی انتخاب شده: {_pipeline_result.reasoning_strategy.value}")
            except HandlerError as _pipe_err:
                logger.warning("v9 pipeline: %s", _pipe_err)
                await agent.log_self_correction("خطا در ارکستراتور، سوئیچ به حالت پایه")
            await agent.complete_step(0)

            # Step 2: RAG & Memory
            await agent.start_step(1)
            await agent.update_thought("در حال بازیابی اطلاعات مرتبط از حافظه...")
            try:
                _rag = get_memory().build_rag_context(text, user_id=str(user_id), max_tokens=16384)
                if _rag:
                    sys_prompt += f"\n\n[USER MEMORY]\n{_rag}\n[/USER MEMORY]"
            except HandlerError as _rag_err:
                logger.warning("v9 RAG: %s", _rag_err)

            # Enhanced prompt via PromptEngine
            try:
                _mode = get_reasoning_mode(text)
                _cfg = PromptConfig(reasoning_mode=_mode)
                _pr = get_prompt_engine().build(text, config=_cfg)
                if hasattr(_pr, 'system_prompt') and _pr.system_prompt:
                    sys_prompt += f"\n\n[ENHANCED CONTEXT]\n{_pr.system_prompt}\n[/ENHANCED CONTEXT]"
            except HandlerError as _pe_err:
                logger.warning("v9 prompt engine: %s", _pe_err)
            await agent.complete_step(1)

            # Step 3: Final Generation
            await agent.start_step(2)
            await agent.update_thought("در حال تولید پاسخ نهایی...", active_model=mk)
            
            # v9.5: Context management — trim to fit model window
            try:
                _ctx_mgr = get_context_manager()
                sys_prompt = _ctx_mgr.trim_to_budget(sys_prompt, max_tokens=163840)
            except HandlerError as _ctx_err:
                logger.debug('Context manager: %s', _ctx_err)

            # Use resilience engine for AI call
            try:
                answer = await agent.execute_with_resilience(
                    func=ai_client.ask,
                    user_id=user_id,
                    text=text,
                    system_prompt=sys_prompt,
                    primary_model_key=mk,
                    use_autotune=cfg["autotune"],
                    step_index=2, # This is the final generation step
                )
            except HandlerError as e:
                await agent.end_thinking(f"❌ خطای نهایی در تولید پاسخ: {e}", success=False)
                raise # Re-raise to be caught by outer handler

            # v9.5: Validate & Hallucination detection
            try:
                _validator = get_output_validator()
                answer = _validator.sanitize(answer)
                _hallu = get_hallucination_detector()
                _hallu_result = _hallu.check(text, answer)
                if _hallu_result.get('risk', 0) > 0.7:
                    answer += '\n\n⚠️ _هشدار: ممکن است این پاسخ حاوی اطلاعات نادقیق باشد._'
            except HandlerError as _val_err:
                logger.debug('Validation/Hallu: %s', _val_err)

            # ── STM post-processing from Extra module ──
            answer = apply_stm_to_response(user_id, answer)

            # ── v9: Store in memory + telemetry
            try:
                _tags = ["ai_chat"]
                get_memory().store(
                    content=f"Q: {text[:300]}\nA: {answer[:500] if answer else ''}",
                    mem_type=MemoryType.CONVERSATION,
                    user_id=str(user_id), tags=_tags,
                )
            except HandlerError as _store_err:
                logger.warning("v9 store: %s", _store_err)
                
            await agent.complete_step(2)

            # ── Post-processing: auto-generate any /image commands ──
            answer = await _process_ai_response_images(message, answer)

            # End thinking and show result
            await agent.end_thinking("پاسخ آماده شد.")
            
            # v27.1: Add model transparency footer
            _transp = ai_client.get_last_transparency()
            if _transp and _transp.get("was_fallback"):
                _actual = _transp.get("actual_model", "")
                from arki_project.utils.models_registry import get_model as _gm_t
                _req_info = _gm_t(_transp.get("requested_key", ""))
                _req_name = _req_info.name if _req_info else _transp.get("requested_key", "")
                answer += f"\n\n_⚡ مدل پاسخ‌دهنده: *{_actual}* (جایگزین رایگان {_req_name})_"
            
            await safe_reply(message, answer)

    except HandlerError as exc:
        logger.error("[%d] AI chat error: %s", user_id, exc, exc_info=True)
        try:
            await message.answer(user_friendly_error(exc))
        except HandlerError as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer("⚠️ خطایی رخ داد. دوباره تلاش کن.")


