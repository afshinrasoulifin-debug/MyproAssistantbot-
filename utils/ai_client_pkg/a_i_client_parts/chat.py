
"""
AIClient — Chat mixin
"""
from __future__ import annotations

import logging

from sqlalchemy import select, delete

try:
    from arki_project.database.connection import get_session
except Exception:
    get_session = None

try:
    from arki_project.database.models import ChatMessage as DBChatMessage
except Exception:
    DBChatMessage = None

try:
    from arki_project.utils.models_core import DEFAULT_MODEL
except Exception:
    DEFAULT_MODEL = "gemini-2.5-pro"

logger = logging.getLogger(__name__)


class AIClientChatMixin:
    """Methods related to chat."""

    async def ask(
        self,
        user_id: int,
        text: str,
        *,
        system_prompt: str | None = None,
        model_key: str | None = None,
        use_autotune: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
        thinking_agent: ThinkingAgentPro | None = None,
    ) -> str:
        """Send text and get an AI reply. Handles fallback automatically."""

        # v27.1: Reset transparency tracking for this call
        self._last_transparency = None

        # Load history from DB on first contact.
        await self._ensure_loaded(user_id)

        # Resolve model.
        mk = model_key or DEFAULT_MODEL
        mk = working_model_key(mk, self._api_key, self._groq_api_key)

        # v26.0: Smart Model Routing — auto-select best model for query
        _selected_tier = "standard"
        _query_type = "general"
        _route = None  # v26.0 safety: always define _route
        _consensus_used = False  # v26.0 safety: always define
        _latency_ms = 0.0  # v26.0 safety: always define
        if _QUALITY_ENGINE:
            try:
                from arki_project.utils.models_registry import get_apex_tier
                _selected_tier = get_apex_tier(mk) or "standard"
                _router = get_smart_router()
                _route = _router.select(text, tier=_selected_tier, user_id=user_id, current_model=mk)
                _query_type = _route.query_type.value
                # Only override if confidence is high and model is in same tier
                if _route.confidence > 0.6 and _route.model_key != mk:
                    from arki_project.utils.models_registry import MODELS
                    if _route.model_key in MODELS:
                        logger.info("SmartRouter: %s → %s (type=%s, conf=%.2f)", mk, _route.model_key, _query_type, _route.confidence)
                        mk = _route.model_key
            except ProviderAuthError as _sr_err:
                logger.debug("SmartRouter: %s", _sr_err)

        # Build params — v10: smart defaults when not specified
        if use_autotune:
            params = autotune(text)
        else:
            # v10: Use smart temperature if not explicitly set
            effective_temp = temperature if temperature is not None else smart_select_temperature(text)
            effective_max = max_tokens if max_tokens is not None else self._max_tokens
            params = {
                "temperature": effective_temp,
                "max_tokens": effective_max,
            }

        # Resolve persona-based system prompt if not overridden.
        if system_prompt is None:
            system_prompt = PERSONAS["assistant"].system_prompt

        # v26.1: Unified language detection — single source of truth
        try:
            from arki_project.utils.lang_detect import detect_language as _detect_lang
            _lang = _detect_lang(text)
        except ImportError:
            _persian_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
            _latin_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
            _lang = "fa" if _persian_chars > _latin_chars else "en"

        # v26.0: Adaptive Prompt — tier-aware system prompt enhancement
        if _QUALITY_ENGINE:
            try:
                _ap = get_adaptive_prompt()
                system_prompt = _ap.build_system_prompt(
                    base_prompt=system_prompt,
                    tier=_selected_tier,
                    query_type=_query_type,
                    language=_lang,
                )
                # Also adjust temperature based on tier
                if not use_autotune and temperature is None:
                    _tier_temp = _ap.get_tier_temperature(_selected_tier, _query_type)
                    params["temperature"] = _tier_temp
            except AIProviderError as _ap_err:
                logger.debug("AdaptivePrompt: %s", _ap_err)

        # Append user message.
        await self._append(user_id, "user", text)

        # Build messages list — v10: smart context packing
        history = self._history[user_id][-self._max_history:]
        msgs = [{"role": "system", "content": system_prompt}]

        # v10: Prioritize recent messages + relevant older ones
        if len(history) > 30:
            # Always include last 15 messages
            recent = history[-15:]
            # Score older messages by relevance to current query
            older = history[:-15]
            query_words = set(text.lower().split())
            scored_older = []
            for m in older:
                m_words = set(m.content.lower().split())
                overlap = len(query_words & m_words)
                scored_older.append((overlap, m))
            scored_older.sort(key=lambda x: x[0], reverse=True)
            # Take top 15 relevant older messages
            relevant_older = [m for _, m in scored_older[:15]]
            # Combine in chronological order
            history = sorted(relevant_older + list(recent), key=lambda m: m.timestamp)
        
        for m in history:
            role = "assistant" if m.role == "model" else m.role
            msgs.append({"role": role, "content": m.content})

        # v9.5: Check response cache first
        _ai_cache = get_ai_cache()
        _cached = _ai_cache.get(text, mk, params.get('temperature', 0.7))
        if _cached:
            logger.debug('AI cache hit for user=%d model=%s', user_id, mk)
            await self._append(user_id, 'model', _cached)
            # v26.1: Track cached responses in analytics too
            if _QUALITY_ENGINE:
                try:
                    _analytics = get_analytics()
                    from arki_project.utils.models_registry import get_model
                    _mi = get_model(mk)
                    # v26.1: Retrieve real quality score from cache metadata
                    _cached_quality = _ai_cache.get_quality(text, mk, params.get('temperature', 0.7))
                    _analytics.record_call(
                        model_key=mk,
                        provider=_mi.provider if _mi else "unknown",
                        success=True,
                        latency_ms=0.0,
                        quality_score=_cached_quality if _cached_quality else 0.8,
                        query_type=_query_type if _query_type else "general",
                    )
                except AIProviderError as _err:
                    logger.warning("Suppressed error: %s", _err)
            return _cached

        # v26.0: Call AI — with Consensus Engine for Pro/Power/Ultra tiers
        _t0 = __import__('time').monotonic()
        _consensus_used = False

        if _QUALITY_ENGINE and _selected_tier in ("pro", "power", "ultra"):
            try:
                _ce = get_consensus_engine()
                _ap_engine = get_adaptive_prompt()
                _cons_cfg = _ap_engine.get_consensus_config(_selected_tier)
                _strategy_name = _cons_cfg["strategy"]
                _num_models = _cons_cfg["num_models"]

                # Get alternative models from smart router
                _alt_models = [mk]
                if _route is not None and hasattr(_route, 'alternatives') and _route.alternatives:
                    for _alt in _route.alternatives:
                        if _alt != mk and _alt not in _alt_models:
                            _alt_models.append(_alt)
                        if len(_alt_models) >= _num_models:
                            break

                # Only run consensus if we have multiple models
                if len(_alt_models) >= 2:
                    _strategy_map = {
                        "race": ConsensusStrategy.RACE,
                        "best_of": ConsensusStrategy.BEST_OF,
                        "consensus": ConsensusStrategy.CONSENSUS,
                    }
                    _strategy = _strategy_map.get(_strategy_name, ConsensusStrategy.BEST_OF)

                    # Create a callable for consensus engine
                    async def _consensus_call_fn(_msgs, _mk, temperature=0.7, max_tokens=65536):
                        return await self._call_with_fallback(
                            _msgs, _mk, user_id=user_id,
                            thinking_agent=thinking_agent,
                            temperature=temperature, max_tokens=max_tokens,
                        )

                    _cons_result = await _ce.run(
                        query=text,
                        messages=msgs,
                        models=_alt_models,
                        call_fn=_consensus_call_fn,
                        strategy=_strategy,
                        timeout_seconds=60.0,
                        temperature=params.get("temperature", 0.7),
                        max_tokens=params.get("max_tokens", 65536),
                    )
                    answer = clean_think_tags(_cons_result.text)
                    _consensus_used = True
                    logger.info(
                        "Consensus[%s] → winner=%s (models=%d, received=%d, quality=%.2f, synthesis=%s)",
                        _strategy.value, _cons_result.winning_model,
                        _cons_result.total_models_queried, _cons_result.responses_received,
                        _cons_result.quality_score, _cons_result.synthesis_used,
                    )
                else:
                    # Only 1 model available — fall back to single call
                    answer = await self._call_with_fallback(msgs, mk, user_id=user_id, thinking_agent=thinking_agent, **params)
                    answer = clean_think_tags(answer)
            except AIProviderError as _ce_err:
                logger.warning("Consensus failed (%s), falling back to single model", _ce_err)
                answer = await self._call_with_fallback(msgs, mk, user_id=user_id, thinking_agent=thinking_agent, **params)
                answer = clean_think_tags(answer)
        else:
            # Standard/Fast: single model call
            answer = await self._call_with_fallback(msgs, mk, user_id=user_id, thinking_agent=thinking_agent, **params)
            answer = clean_think_tags(answer)

        _latency_ms = (__import__('time').monotonic() - _t0) * 1000

        # v26.0: Deep Quality Evaluation — score response quality
        _quality_score = 0.0
        if _QUALITY_ENGINE and answer and answer.strip():
            try:
                _qg = _get_qg()
                _lang_detect = _lang  # v26.1: Use pre-computed language
                _qr = _qg.deep_evaluate(
                    response=answer,
                    query=text,
                    category="chat",
                    language=_lang_detect,
                    tier=_selected_tier,
                )
                _quality_score = _qr.overall_score

                # Auto-retry on very low quality for Pro/Ultra (only once)
                if not _qr.passed and _selected_tier in ("pro", "power", "ultra") and not _consensus_used:
                    logger.info(
                        "Quality gate FAILED (score=%.2f, tier=%s) — retrying with fallback",
                        _quality_score, _selected_tier,
                    )
                    _retry_t0 = __import__('time').monotonic()
                    # v26.1: Prefer alternative model for retry (avoid same bad output)
                    _retry_mk = mk
                    if _route is not None and hasattr(_route, 'alternatives') and _route.alternatives:
                        for _alt_mk in _route.alternatives:
                            if _alt_mk != mk:
                                _retry_mk = _alt_mk
                                break
                    _retry_answer = await self._call_with_fallback(
                        msgs, _retry_mk, user_id=user_id,
                        thinking_agent=thinking_agent, **params,
                    )
                    _retry_answer = clean_think_tags(_retry_answer)
                    _retry_qr = _qg.deep_evaluate(
                        response=_retry_answer, query=text,
                        category="chat", language=_lang_detect, tier=_selected_tier,
                    )
                    _retry_latency = (__import__('time').monotonic() - _retry_t0) * 1000
                    _latency_ms += _retry_latency
                    if _retry_qr.overall_score > _quality_score:
                        answer = _retry_answer
                        _quality_score = _retry_qr.overall_score
                        logger.info("Retry improved quality: %.2f → %.2f", _qr.overall_score, _quality_score)
                    else:
                        logger.info("Retry did not improve (%.2f vs %.2f), keeping original", _retry_qr.overall_score, _quality_score)
            except AIProviderError as _qg_err:
                logger.debug("QualityGate: %s", _qg_err)

        # Save answer.
        await self._append(user_id, "model", answer)

        # v26.0: Performance Analytics — track with REAL latency & quality
        if _QUALITY_ENGINE:
            try:
                _analytics = get_analytics()
                from arki_project.utils.models_registry import get_model
                _mi = get_model(mk)
                _analytics.record_call(
                    model_key=mk,
                    provider=_mi.provider if _mi else "unknown",
                    success=bool(answer and answer.strip()),
                    latency_ms=_latency_ms,
                    quality_score=_quality_score,
                    query_type=_query_type if _query_type else "general",
                )
                # Also update smart router with performance data
                _router = get_smart_router()
                _router.update_performance(
                    mk, bool(answer and answer.strip()), _latency_ms,
                    quality_score=_quality_score, query_type=_query_type,
                )
            except AIProviderError as _an_err:
                logger.debug("Analytics: %s", _an_err)

        # v9.5: Cache the response — v26.1: include quality score
        _ai_cache.set(text, mk, answer, params.get('temperature', 0.7), quality_score=_quality_score)

        # v9.6: Update user's daily token usage in DB
        try:
            _token_count = len(text.split()) + len(answer.split())
            from arki_project.database.connection import get_session
            from sqlalchemy import update as _sql_update
            from arki_project.database.models import User as _UserModel
            async with get_session() as _ts:
                await _ts.execute(
                    _sql_update(_UserModel)
                    .where(_UserModel.telegram_id == user_id)
                    .values(tokens_used_today=_UserModel.tokens_used_today + _token_count)
                )
                await _ts.commit()
        except AIProviderError as _tu_err:
            logger.debug('Token usage update: %s', _tu_err)

        # v9.5: Track AI cost
        try:
            tracker = get_cost_tracker()
            tracker.record(
                user_id=user_id, model=mk, handler="ask",
                input_tokens=len(text.split()),
                output_tokens=len(answer.split()),
            )
        except AIProviderError as _cost_err:
            logger.debug('Cost tracking: %s', _cost_err)

        # v9.7: Push Prometheus metrics
        try:
            if _push_prom:
                _input_tok = len(text.split())
                _output_tok = len(answer.split())
                _model_info = get_model(mk)
                _push_prom(
                    model=mk,
                    provider=_model_info.provider,
                    input_tokens=_input_tok,
                    output_tokens=_output_tok,
                    cost=0.0,
                    latency=_latency_ms / 1000 if _latency_ms else 0.0,
                )
        except AIProviderError as _prom_err:
            logger.debug('Prometheus push: %s', _prom_err)

        # v3.3: Emit event for automation
        if _INTERNAL_MGMT:
            try:
                bus = get_event_bus()
                import asyncio
                asyncio.ensure_future(bus.publish("ai.response", {
                    "user_id": user_id, "model": mk,
                    "tokens": len(answer.split()) * 2,
                    "cached": False,
                }))
            except AIProviderError:
                pass
        return answer

    async def ask_raw(
        self,
        messages: list[dict],
        model_key: str,
        *,
        user_id: int = 0,
        temperature: float = 0.7,
        max_tokens: int = 65536,
        top_p: float | None = None,
        tools: list | None = None,
    ) -> str:
        """Low-level call without history or persistence."""
        mk = working_model_key(model_key, self._api_key, self._groq_api_key)
        answer = await self._call_with_fallback(
            messages, mk,
            user_id=user_id,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            tools=tools,
        )
        return clean_think_tags(answer)

    async def ask_streaming(
        self,
        messages: list,
        model_key: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        *,
        bot=None,
        chat_id: int = 0,
        message_id: int = 0,
        use_grounding: bool = False,
    ):
        """
        Streaming AI response — edits Telegram message progressively.
        Falls back to normal ask_raw if streaming not supported.

        Usage:
            result = await ai_client.ask_streaming(
                messages=msgs, model_key=mk,
                bot=bot, chat_id=chat_id, message_id=msg.message_id,
            )
        """
        import asyncio
        import json as _json

        mk = model_key or DEFAULT_MODEL
        mk = working_model_key(mk, self._api_key, self._groq_api_key)
        model_info = get_model(mk)

        if model_info.provider != "gemini":
            # Non-Gemini: fall back to normal call
            return await self.ask_raw(messages, mk, temperature=temperature, max_tokens=max_tokens)

        # Build Gemini-format messages
        sys_text = ""
        contents: list = []
        for m in messages:
            role = m.get("role", "user") if isinstance(m, dict) else "user"
            text = m.get("content", "") if isinstance(m, dict) else str(m)
            if role == "system":
                sys_text = text
            elif role in ("assistant", "model"):
                contents.append({"role": "model", "parts": [{"text": text}]})
            else:
                contents.append({"role": "user", "parts": [{"text": text}]})

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"},
            ],
        }
        if sys_text:
            payload["systemInstruction"] = {"parts": [{"text": sys_text}]}
        if use_grounding:
            payload["tools"] = [{"google_search": {}}]
            payload["tool_config"] = {"function_calling_config": {"mode": "AUTO"}}

        url = f"{self._base_url}/models/{model_info.id}:streamGenerateContent"

        # Gemini streaming via shared aiohttp pool
        try:
            client = await self._get_pool_client("gemini_stream")
            accumulated = ""
            last_edit = 0.0

            async with client.post(
                url,
                json=payload,
                headers={"x-goog-api-key": self._api_key},
                params={"alt": "sse"},
            ) as resp:
                if resp.status != 200:
                    # Non-200: fall back to normal call
                    return await self.ask_raw(messages, mk, temperature=temperature, max_tokens=max_tokens)

                buffer = ""
                async for chunk in resp.content.iter_any():
                    buffer += chunk.decode("utf-8", errors="ignore")
                    # Process complete JSON objects in the stream
                    while True:
                        # Find complete JSON chunk
                        start = buffer.find("{")
                        if start == -1:
                            buffer = ""
                            break
                        depth = 0
                        end = -1
                        for i in range(start, len(buffer)):
                            if buffer[i] == "{":
                                depth += 1
                            elif buffer[i] == "}":
                                depth -= 1
                                if depth == 0:
                                    end = i + 1
                                    break
                        if end == -1:
                            break  # Incomplete JSON — wait for more data

                        json_str = buffer[start:end]
                        buffer = buffer[end:]

                        try:
                            chunk_data = _json.loads(json_str)
                            parts = (
                                chunk_data.get("candidates", [{}])[0]
                                .get("content", {})
                                .get("parts", [])
                            )
                            text = "".join(p.get("text", "") for p in parts)
                            if text:
                                accumulated += text
                                # Edit message every 0.5s to avoid Telegram rate limits
                                now = asyncio.get_running_loop().time()
                                if bot and chat_id and message_id and now - last_edit > 0.5:
                                    try:
                                        await bot.edit_message_text(
                                            text=accumulated[:4000],
                                            chat_id=chat_id,
                                            message_id=message_id,
                                        )
                                        last_edit = now
                                    except AIProviderError as _e:
                                        logger.debug("Suppressed: %s", _e)  # v10.1: no longer silent
                        except (_json.JSONDecodeError, IndexError, KeyError):
                            continue

            # Final edit with complete text
            if bot and chat_id and message_id and accumulated:
                try:
                    await bot.edit_message_text(
                        text=accumulated[:4000],
                        chat_id=chat_id,
                        message_id=message_id,
                    )
                except AIProviderError as _e:
                    logger.debug("Suppressed: %s", _e)  # v10.1: no longer silent

            return accumulated or await self.ask_raw(
                messages, mk, temperature=temperature, max_tokens=max_tokens,
            )


        except AIProviderError:
            # Fallback to normal (non-streaming)
            return await self.ask_raw(messages, mk, temperature=temperature, max_tokens=max_tokens)

    async def chat(
        self,
        user_id: int,
        message: str,
        **kwargs: object,
    ) -> str:
        """Alias for ask() — used by sales handlers."""
        return await self.ask(user_id, message, **kwargs)

    async def clear_history(self, user_id: int) -> None:
        self._history.pop(user_id, None)
        self._loaded_users.discard(user_id)
        async with get_session() as session:
            await session.execute(
                delete(DBChatMessage).where(
                    DBChatMessage.user_id == user_id,
                ),
            )



