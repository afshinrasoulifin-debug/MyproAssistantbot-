
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""


tg_bot/handlers/compare.py
──────────────────────────
Multi-model commands:

  /compare   — side-by-side comparison of 2 models
  /consensus — query 3-4 models and synthesize
"""


import asyncio
import logging

from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import Message

from arki_project.config import Settings
from arki_project.utils.ai_client import AIClient
from arki_project.utils.models_registry import (
    MODELS,
    split_for_telegram,
    user_friendly_error,
)
from arki_project.utils.safe_send import safe_delete, safe_reply
from arki_project.handlers.shared import extract_args
from arki_project.utils.v7_core import (


# ── Infrastructure access (injected by middleware) ──

# Access via data["infra_registry"], data["infra_event_bus"], data["infra_config"]

    enhance_system_prompt, store_result, get_pipeline,
)

logger = logging.getLogger(__name__)
router = Router(name="compare")




# ═══════════ /compare ═══════════

@router.message(Command("compare"))
async def cmd_compare(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    query = extract_args(message.text or "", "/compare")
    if not query:
        await safe_reply(message, "⚔️ `/compare سوال` — مقایسه ۲ مدل")
        return

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )

    # Pick 2 models (one from each provider if possible).
    pairs: list[str] = []
    if settings.ai_api_key:
        pairs.append("gemini-pro")
    if settings.groq_api_key:
        pairs.append("llama70")
    if len(pairs) < 2:
        if settings.ai_api_key:
            pairs.append("gemini-pro")
        elif settings.groq_api_key:
            pairs.append("qwen3")
    if len(pairs) < 2:
        await message.answer("❌ حداقل ۲ مدل لازم")
        return

    try:
        msgs = [{"role": "user", "content": query}]
        r1, r2 = await asyncio.gather(
            ai_client.ask_raw(msgs, pairs[0], max_tokens=32768),
            ai_client.ask_raw(msgs, pairs[1], max_tokens=32768),
        )

        m1 = MODELS[pairs[0]]
        m2 = MODELS[pairs[1]]
        output = (
            f"⚔️ *مقایسه:* _{query}_\n\n"
            f"━━ {m1.emoji} *{m1.name}* ━━\n{r1}\n\n"
            f"━━ {m2.emoji} *{m2.name}* ━━\n{r2}"
        )

        for chunk in split_for_telegram(output):
            try:
                await safe_reply(message, chunk)
            except HandlerError as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════ /consensus ═══════════

@router.message(Command("consensus"))
async def cmd_consensus(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    query = extract_args(message.text or "", "/consensus")
    if not query:
        await safe_reply(message, "🏆 `/consensus سوال` — اجماع چند مدل")
        return

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )

    # Build model pool (up to 4).
    pool: list[str] = []
    if settings.ai_api_key:
        pool += ["gemini-pro", "gemini-pro", "gemini2-flash"]
    if settings.groq_api_key:
        pool += ["llama70", "qwen3", "llama-scout"]
    pool = pool[:4]

    if len(pool) < 2:
        await message.answer("❌ حداقل ۲ مدل لازم")
        return

    try:
        msgs = [{"role": "user", "content": query}]
        results = await asyncio.gather(
            *[ai_client.ask_raw(msgs, mk, max_tokens=32768) for mk in pool],
            return_exceptions=True,
        )

        output = f"🏆 *اجماع {len(pool)} مدل:* _{query}_\n\n"
        answers: list[str] = []

        for mk, result in zip(pool, results):
            m = MODELS[mk]
            if isinstance(result, Exception):
                output += f"❌ {m.emoji} *{m.name}*: خطا\n\n"
            else:
                answers.append(result)
                output += f"━━ {m.emoji} *{m.name}* ━━\n{result}\n\n"

        # Synthesize if we got at least 2 answers.
        if len(answers) >= 2:
            synth_mk = "gemini-pro" if settings.ai_api_key else "llama70"
            import time as _t
            _t0 = _t.time()
            _sys_enhanced = enhance_system_prompt(
                "You are a comparative analysis expert. Analyze differences clearly.",
                user_text=query, user_id=str(message.from_user.id) if message.from_user else "0"
            )
            synth = await ai_client.ask_raw(
                messages=[
                    {
                        "role": "system",
                        "content": _sys_enhanced,
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Question: {query}\n\nAnswers:\n"
                            + "\n---\n".join(answers)
                        ),
                    },
                ],
                model_key=synth_mk,
                temperature=0.4,
                max_tokens=16384,
            )
            store_result(message.from_user.id if message.from_user else 0, query[:300], synth[:500] if synth else "", "compare", duration_s=_t.time()-_t0)
            output += f"━━ 🏆 *نتیجه نهایی* ━━\n{synth}"

        for chunk in split_for_telegram(output):
            try:
                await safe_reply(message, chunk)
            except HandlerError as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════ /debate — Multi-LLM Debate via multi_llm_orchestrator ═══════════

@router.message(Command("debate"))
async def cmd_debate(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """Multi-round debate: models argue, refine, and reach consensus."""
    query = extract_args(message.text or "", "/debate")
    if not query:
        await safe_reply(message, "🗣️ `/debate سوال` — بحث چند مدل + رسیدن به اجماع\n\n"
            "_مدل‌ها با هم بحث می‌کنن و نتیجه نهایی رو بهت می‌دن._")
        return

    import os
    # v25.0 AUTONOMOUS: Resolve key from all sources
    or_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not or_key:
        try:
            from arki_project.utils.free_access_router import get_free_router
            _pk = get_free_router()._provisioned_keys.get("openrouter_free", [])
            or_key = _pk[0] if _pk else ""
        except HandlerError:
            or_key = ""

    await message.bot.send_chat_action(
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )
    status = await message.answer("🗣️ مدل‌ها دارن بحث می‌کنن...")

    try:
        import time as _t
        _t0 = _t.time()

        from arki_project.utils.multi_llm_orchestrator import debate
        result = await debate(
            query=query,
            api_key=or_key,
            max_rounds=2,
        )

        await safe_delete(status)

        # Format output
        output = f"🗣️ *بحث مدل‌ها:* _{query}_\n\n"
        output += f"*مدل‌های شرکت‌کننده:* {', '.join(result.selected_models)}\n"
        output += f"*اطمینان:* {result.confidence:.0%}\n\n"

        # Individual model responses
        for resp in result.models:
            output += f"━━ *{resp.model_id}* ━━\n{resp.content[:500]}\n\n"

        # Final synthesis
        output += f"━━ 🏆 *نتیجه نهایی* ━━\n{result.final_response}"

        _duration = _t.time() - _t0
        store_result(
            message.from_user.id if message.from_user else 0,
            query[:300], result.final_response[:500] if result.final_response else "",
            "debate", duration_s=_duration,
        )




        # Pipeline tracking
        try:
            pipeline = get_pipeline()
            pr = await pipeline.process(user_id=message.from_user.id if message.from_user else 0, text=query)
            logger.info("Debate pipeline: cat=%s strategy=%s", pr.category.value, pr.reasoning_strategy.value)
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)

        for chunk in split_for_telegram(output):
            try:
                await safe_reply(message, chunk)
            except HandlerError:
                await message.answer(chunk)

    except HandlerError as exc:
        logger.error("Debate failed: %s", exc, exc_info=True)
        try:
            await safe_delete(status)
        except HandlerError as e:
            logger.debug("Suppressed: %s", e)
        await message.answer(user_friendly_error(exc))


