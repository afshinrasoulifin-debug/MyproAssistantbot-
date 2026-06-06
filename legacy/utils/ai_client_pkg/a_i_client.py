
"""
ai_client_pkg/a_i_client.py — AIClient
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class AIClient:
    """Stateful AI client — multi-model, multi-provider, persistent."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        model: str = "gemini-2.5-pro",  # v10.2: Pro default
        max_history: int = 500,  # v9.7.1: Deep context
        temperature: float = 0.7,
        max_tokens: int = 65536,  # v10.2: TITANIUM unlimited
        groq_api_key: str = "",
        openrouter_api_key: str = "",
    ) -> None:
        self._api_key = api_key
        # v3.3: Register keys with internal key manager for rotation
        if _INTERNAL_MGMT:
            try:
                km = get_key_manager()
                if api_key:
                    km.add_key("gemini", api_key, label="primary_gemini")
                if groq_api_key:
                    km.add_key("groq", groq_api_key, label="primary_groq")
                if openrouter_api_key:
                    km.add_key("openrouter", openrouter_api_key, label="primary_openrouter")
                km.load_from_env()  # Load any additional keys from env
                logger.info("v3.3: Internal key manager initialized with %s",
                           {p: km.get_provider_status(p)["total_keys"]
                            for p in ["gemini", "groq", "openrouter"]})
            except Exception as e:
                logger.debug("Key manager init: %s (non-fatal)", e)
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._max_history = max_history
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._groq_api_key = groq_api_key
        self._openrouter_api_key = openrouter_api_key
        # In-memory caches.
        self._history: Dict[int, List[ChatMessage]] = defaultdict(list)
        self._loaded_users: set[int] = set()
        self._config_cache: dict[int, tuple[float, dict]] = {}  # user_id → (timestamp, config)
        self._config_cache_ttl: float = 300.0  # 5 minutes
        # Use centralized HTTP pool (shared across all modules)
        # No duplicate clients — saves memory and connections
        from arki_project.utils.http_pool import get_client as _get_pool_client
        self._get_pool_client = _get_pool_client
        # v9.5: Circuit breaker per provider
        self._breakers = {
            'gemini': CircuitBreaker('gemini', failure_threshold=5, recovery_timeout=60.0),
            'groq': CircuitBreaker('groq', failure_threshold=5, recovery_timeout=60.0),
            'openrouter': CircuitBreaker('openrouter', failure_threshold=3, recovery_timeout=120.0),
        }

    async def close(self) -> None:
        """Close HTTP clients and release resources."""
        from arki_project.utils.http_pool import close_all
        await close_all()
        self._breakers.clear()  # v9.8.7: was _circuit_breakers (wrong name)

    # ─────── Public: high-level ask ───────

    def get_last_transparency(self) -> "Optional[Dict[str, Any]]":
        """Get transparency info about the last model call.
        Returns dict with actual_model, was_fallback, etc. or None."""
        return self._last_transparency

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
            except Exception as _sr_err:
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
            except Exception as _ap_err:
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
                except Exception as _err:
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
            except Exception as _ce_err:
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
            except Exception as _qg_err:
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
            except Exception as _an_err:
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
        except Exception as _tu_err:
            logger.debug('Token usage update: %s', _tu_err)

        # v9.5: Track AI cost
        try:
            tracker = get_cost_tracker()
            tracker.record(
                user_id=user_id, model=mk, handler="ask",
                input_tokens=len(text.split()),
                output_tokens=len(answer.split()),
            )
        except Exception as _cost_err:
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
        except Exception as _prom_err:
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
            except Exception:
                pass
        return answer

    async def chat(
        self,
        user_id: int,
        message: str,
        **kwargs: object,
    ) -> str:
        """Alias for ask() — used by sales handlers."""
        return await self.ask(user_id, message, **kwargs)

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

    async def clear_history(self, user_id: int) -> None:
        self._history.pop(user_id, None)
        self._loaded_users.discard(user_id)
        async with get_session() as session:
            await session.execute(
                delete(DBChatMessage).where(
                    DBChatMessage.user_id == user_id,
                ),
            )

    # ─────── User config ───────

    async def get_user_config(self, user_id: int) -> dict:
        """Return dict with model, persona, autotune, voice (cached)."""
        if user_id in self._config_cache:
            cached_at, cached_val = self._config_cache[user_id]
            if time.time() - cached_at < self._config_cache_ttl:
                return cached_val
            del self._config_cache[user_id]

        async with get_session() as session:
            result = await session.execute(
                select(UserConfig).where(
                    UserConfig.telegram_id == user_id,
                ),
            )
            cfg = result.scalar_one_or_none()
            if cfg is None:
                result_dict = {
                    "model": DEFAULT_MODEL,
                    "persona": "assistant",
                    "autotune": True,
                    "voice": "Zephyr",
                }
            else:
                result_dict = {
                    "model": cfg.model,
                    "persona": cfg.persona,
                    "autotune": cfg.autotune,
                    "voice": cfg.voice,
                }

        self._config_cache[user_id] = (time.time(), result_dict)
        return result_dict

    async def set_user_config(
        self, user_id: int, key: str, value: object
    ) -> None:
        self._config_cache.pop(user_id, None)  # invalidate cache
        async with get_session() as session:
            result = await session.execute(
                select(UserConfig).where(
                    UserConfig.telegram_id == user_id,
                ),
            )
            cfg = result.scalar_one_or_none()
            if cfg is None:
                cfg = UserConfig(telegram_id=user_id)
                session.add(cfg)
                await session.flush()
            setattr(cfg, key, value)
            await session.flush()

    # ─────── Provider calls ───────


    # ── Infrastructure Integration ──
    # REMOVED: _get_infra_gateway + _notify_infra (orphan code — never called anywhere)



    async def _get_rotated_key(self, provider: str) -> str:
        """v3.3: Get API key from rotation pool, fallback to primary."""
        if _INTERNAL_MGMT:
            try:
                km = get_key_manager()
                key = await km.get_key(provider)
                if key:
                    return key
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)
        # Fallback to primary keys
        if provider == "gemini":
            return self._api_key
        elif provider == "groq":
            return self._groq_api_key
        elif provider == "openrouter":
            return self._openrouter_api_key
        return self._api_key

    async def _call_gemini(
        self,
        msgs: list[dict],
        model_id: str,
        temperature: float = 0.7,
        max_tokens: int = 65536,
        tools: list | None = None,
        *,
        top_p: float | None = None,
        thinking_agent: ThinkingAgentPro | None = None,
        **_: object,
    ) -> str:
        sys_text = ""
        contents: list[dict] = []
        for m in msgs:
            if m["role"] == "system":
                sys_text = m["content"]
            elif m["role"] == "user":
                contents.append(
                    {"role": "user", "parts": [{"text": m["content"]}]},
                )
            elif m["role"] in ("assistant", "model"):
                contents.append(
                    {"role": "model", "parts": [{"text": m["content"]}]},
                )

        gen_cfg: dict = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
        if top_p is not None:
            gen_cfg["topP"] = min(top_p, 1.0)

        body: dict = {
            "contents": contents,
            "generationConfig": gen_cfg,
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"},  # v9.7.1
            ],
        }
        if sys_text:
            body["systemInstruction"] = {"parts": [{"text": sys_text}]}
        if tools:
            body["tools"] = tools

        url = f"{self._base_url}/models/{model_id}:generateContent"
        _key = await self._get_rotated_key("gemini")
        headers = {"x-goog-api-key": _key}

        # http_pool.get_client is async → must await
        client = await self._get_pool_client("gemini")
        async with client.post(url, json=body, headers=headers) as resp:
            status = resp.status          # aiohttp: .status (not .status_code)
            data = await resp.json()      # aiohttp: await .json() (not sync)

        if status == 429:
            if thinking_agent:
                await thinking_agent.log_resilience_event("RateLimit", "Gemini 429: Rate limit exceeded", log_level="error")
            if _INTERNAL_MGMT:
                try:
                    km = get_key_manager()
                    await km.report_error("gemini", _key, "rate_limit", is_rate_limit=True)
                except Exception as _err:
                    logger.warning("Suppressed error: %s", _err)
            raise RateLimitError("gemini 429")
        if status in (503, 500, 502):
            if thinking_agent:
                await thinking_agent.log_resilience_event("Overloaded", f"Gemini HTTP {status}: Overloaded", log_level="error")
            raise OverloadedError(f"gemini HTTP {status}")
        if status != 200:
            err = data.get("error", {}).get("message", f"HTTP {status}")
            lo = err.lower()
            if any(w in lo for w in ("high demand", "overloaded", "unavailable", "capacity")):
                if thinking_agent:
                    await thinking_agent.log_resilience_event("Overloaded", f"Gemini: {err}", log_level="error")
                raise OverloadedError(err)
            raise Exception(err)

        cands = data.get("candidates", [])
        if not cands:
            fb = data.get("promptFeedback", {}).get("blockReason", "")
            error_msg = f"No response{f' ({fb})' if fb else ''}"
            if thinking_agent:
                await thinking_agent.log_resilience_event("NoResponse", f"Gemini: {error_msg}", log_level="error")
            raise Exception(error_msg)
        return "".join(
            p.get("text", "")
            for p in cands[0].get("content", {}).get("parts", [])
        )

    async def _call_groq(
        self,
        msgs: list[dict],
        model_id: str,
        temperature: float = 0.7,
        max_tokens: int = 32768,
        **_: object,
    ) -> str:
        body = {
            "model": model_id,
            # Groq Compound: built-in web search (free)
            **({"tools": [{"type": "web_search"}], "tool_choice": "auto"}
               if "compound" in (model_id or "") else {}),
            "messages": msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        client = await self._get_pool_client("groq")
        async with client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {await self._get_rotated_key('groq')}",
                "Content-Type": "application/json",
            },
            json=body,
        ) as resp:
            status = resp.status
            data = await resp.json()

        if status == 429:
            raise RateLimitError("groq 429")
        if status in (503, 500, 502):
            raise OverloadedError(f"groq HTTP {status}")
        if status != 200:
            err = data.get("error", {}).get("message", f"HTTP {status}")
            raise Exception(err)
        choices = data.get("choices", [])
        if not choices:
            error_msg = "Groq: no response"
            if thinking_agent:
                await thinking_agent.log_resilience_event("NoResponse", error_msg, log_level="error")
            raise Exception(error_msg)
        return choices[0]["message"]["content"]

    async def _call_openrouter(
        self,
        msgs: list[dict],
        model_id: str = "",
        temperature: float = 0.7,
        max_tokens: int = 65536,
        **_: object,
    ) -> str:
        """
        OpenRouter — universal fallback with access to 200+ models.

        Uses free tier models when no API key is set, or paid models
        when OPENROUTER_API_KEY is provided.
        """
        use_model = model_id or OPENROUTER_FALLBACK_MODEL

        # Resolve API key FIRST — needed by routing logic below
        _or_key = self._openrouter_api_key
        if not _or_key:
            try:
                from arki_project.utils.free_access_router import get_free_router
                _pk = get_free_router()._provisioned_keys.get("openrouter_free", [])
                _or_key = _pk[0] if _pk else ""
            except Exception:
                _or_key = ""

        # v28.0: If user HAS an OpenRouter API key → use exact model (no fallback)
        # Only route to free variants when NO key is available
        if _or_key:
            logger.debug("🔑 OpenRouter key present — direct call: %s", use_model)
        elif _FREE_ACCESS:
            try:
                from arki_project.utils.free_access_router import (
                    OPENROUTER_FREE_MODELS, SMART_FALLBACK_MAP,
                )
                # Priority 1: Direct :free variant (same model, free tier)
                free_variant = OPENROUTER_FREE_MODELS.get(use_model)
                if free_variant:
                    use_model = free_variant
                    logger.debug("🤖 Free variant: %s → %s", model_id, use_model)
                else:
                    # Priority 2: Smart Fallback for paid models (no key)
                    fb_chain = SMART_FALLBACK_MAP.get(use_model, [])
                    if fb_chain:
                        from arki_project.utils.models_registry import MODELS
                        for fb_key in fb_chain:
                            fb_model = MODELS.get(fb_key)
                            if fb_model:
                                fb_free = OPENROUTER_FREE_MODELS.get(fb_model.id)
                                if fb_free:
                                    use_model = fb_free
                                    logger.debug("🤖 Smart Fallback: %s → %s → %s", model_id, fb_key, use_model)
                                    break
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)

        body = {
            "model": use_model,
            "messages": msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "HTTP-Referer": "https://arki-engine.app",  # v25.0: Required for :free tier
            "X-Title": "Arki Engine",
        }
        if _or_key:
            headers["Authorization"] = f"Bearer {_or_key}"

        client = await self._get_pool_client("openrouter")
        async with client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=body,
        ) as resp:
            status = resp.status
            data = await resp.json()

        if status == 429:
            raise RateLimitError("openrouter 429")
        if status in (503, 500, 502):
            raise OverloadedError(f"openrouter HTTP {status}")
        if status != 200:
            err = data.get("error", {}).get("message", f"HTTP {status}")
            raise Exception(err)
        choices = data.get("choices", [])
        if not choices:
            raise Exception("OpenRouter: no response")
        return choices[0]["message"]["content"]

    async def _call_with_fallback(
        self,
        msgs: list[dict],
        model_key: str,
        *,
        user_id: int = 0,
        temperature: float = 0.7,
        max_tokens: int = 65536,
        top_p: float | None = None,
        tools: list | None = None,
        thinking_agent: ThinkingAgentPro | None = None,
        **kw: object,
    ) -> str:
        # ── v10: TITANIUM AI Orchestrator (highest priority) ──
        # Routes through shielded client with L1-L3 security,
        # race mode, CSPRNG weighted selection, and 4-level fallback
        try:
            from arki_project.utils.titanium.ai_orchestrator import get_titanium_orchestrator, AITier
            from arki_project.utils.titanium.rate_limiter import get_rate_limiter

            ti_orch = get_titanium_orchestrator()
            if ti_orch is not None:
                # L5: Rate limiting check
                limiter = get_rate_limiter()
                rate_key = f"user:{user_id}"
                if not limiter.check(rate_key):
                    logger.warning("TITANIUM rate limit hit for user %d", user_id)
                    if thinking_agent:
                        await thinking_agent.log_resilience_event("RateLimit", f"TITANIUM rate limit hit for user {user_id}", log_level="warning")
                    # Fall through to orchestrator (rate limited → no TITANIUM)
                else:
                    # Parse tier command from last message
                    last_text = msgs[-1].get("content", "") if msgs else ""
                    from arki_project.utils.titanium.ai_orchestrator import parse_tier_command
                    tier_cmd, clean_text = parse_tier_command(last_text)

                    # If tier command found, replace last message text
                    dispatch_msgs = list(msgs)
                    if tier_cmd and clean_text != last_text:
                        dispatch_msgs = msgs[:-1] + [{"role": "user", "content": clean_text}]

                    result = await ti_orch.dispatch(
                        dispatch_msgs,
                        tier=tier_cmd,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        user_id=user_id,
                    )
                    if result.success:
                        logger.info(
                            "TITANIUM → tier=%s provider=%s (%.0fms, depth=%d)",
                            result.tier.value, result.provider_id,
                            result.latency_ms, result.fallback_depth,
                        )
                        return result.text

                    logger.warning(
                        "TITANIUM all tiers failed (%s), falling to orchestrator",
                        result.error,
                    )
                    if thinking_agent:
                        await thinking_agent.log_resilience_event("Fallback", f"TITANIUM all tiers failed: {result.error}", log_level="warning")
        except ImportError:
            pass  # TITANIUM not installed
        except Exception as _ti_err:
            logger.debug("TITANIUM unavailable: %s", _ti_err)
            if thinking_agent:
                await thinking_agent.log_resilience_event("Error", f"TITANIUM unavailable: {_ti_err}", log_level="error")

        # ── v9.8.7: Try orchestration layer ──
        try:
            from arki_project.orchestration import get_orchestrator
            orch = get_orchestrator()
            resp = await orch.generate(
                prompt=msgs[-1]["content"] if msgs else "",
                messages=msgs,
                model_key=model_key,
                user_id=user_id,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                tools=tools,
            )
            if resp.ok:
                logger.debug(
                    "Orchestrator → %s:%s (%.0fms, cached=%s)",
                    resp.provider.value, resp.model_id,
                    resp.latency_ms, resp.cached,
                )
                return resp.text
                logger.warning(
                    "Orchestrator error (%s), falling back to legacy",
                    resp.error,
                )
                if thinking_agent:
                    await thinking_agent.log_resilience_event("Fallback", f"Orchestrator error: {resp.error}", log_level="warning")
        except RuntimeError as _e:
            logger.debug("RuntimeError suppressed: %s", _e)
        except ImportError:
            pass
        except Exception as _orch_err:
            logger.debug("Orchestrator unavailable: %s, using legacy", _orch_err)
            if thinking_agent:
                await thinking_agent.log_resilience_event("Error", f"Orchestrator unavailable: {_orch_err}", log_level="error")

        # ── Legacy fallback (original logic) ──
        return await self._call_with_fallback_legacy(
            msgs, model_key,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            tools=tools,
        )

    async def _call_with_fallback_legacy(
        self,
        msgs: list[dict],
        model_key: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 65536,
        top_p: float | None = None,
        tools: list | None = None,
        thinking_agent: ThinkingAgentPro | None = None,
        **kw: object,
    ) -> str:
        """Original _call_with_fallback logic — used when orchestrator is unavailable."""
        info = get_model(model_key)
        provider = info.provider
        model_id = info.id

        # v9.5: Check model deprecation
        try:
            _watcher = get_model_watcher()
            _alt = _watcher.get_active_model(model_key)
            if _alt and _alt != model_key:
                logger.info('Model watcher: %s → %s (deprecated/down)', model_key, _alt)
                model_key = _alt
                info = get_model(model_key)
                provider = info.provider
                model_id = info.id
        except Exception as _mw_err:
            logger.debug('Model watcher: %s', _mw_err)

        # v28.0: DIRECT OpenRouter call when user has API key — bypasses free router
        # This ensures elite/paid models are called EXACTLY as selected
        if provider == "openrouter" and self._openrouter_api_key:
            try:
                result = await self._call_openrouter(
                    msgs, model_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                self._last_transparency = {
                    "actual_model": model_id,
                    "actual_key": model_key,
                    "was_fallback": False,
                    "requested_key": model_key,
                    "route": "direct_openrouter_paid",
                }
                logger.info("🔑 Direct OpenRouter → %s (%s)", model_key, model_id)
                if _METRICS:
                    record_request(provider, model_id, "direct_openrouter_success", 0.0)
                return result
            except (RateLimitError, OverloadedError) as _or_err:
                logger.warning("Direct OpenRouter %s hit %s — falling to free router", model_id, _or_err)
            except Exception as _or_err:
                logger.warning("Direct OpenRouter %s failed: %s — falling to free router", model_id, _or_err)

        # v25.0 AUTONOMOUS: Free access is the PRIMARY path when no paid key
        if _FREE_ACCESS:
            try:
                free_router = get_free_router()
                free_result = await free_router.execute_free_call(
                    model_key, msgs, temperature, max_tokens,
                    _return_metadata=True,
                )
                if free_result:
                    # Store transparency metadata for response footer
                    _fr_meta = None
                    _fr_text = free_result
                    if hasattr(free_result, 'text'):
                        _fr_text = free_result.text
                        _fr_meta = free_result
                        self._last_transparency = {
                            "actual_model": free_result.actual_model_name,
                            "actual_key": free_result.actual_model_key,
                            "was_fallback": free_result.was_fallback,
                            "requested_key": model_key,
                            "route": free_result.route_method,
                        }
                    else:
                        self._last_transparency = None
                    logger.info("🤖 AUTONOMOUS → %s (zero cost, zero key)%s", model_key,
                        f" [actual: {free_result.actual_model_name}]" if _fr_meta and _fr_meta.was_fallback else "")
                    if _METRICS:
                        record_request(provider, model_id, "autonomous_success", 0.0)
                    return _fr_text if '_fr_text' in dir() else free_result
                else:
                    logger.debug("Free route returned empty for %s, trying legacy", model_key)
            except Exception as _free_err:
                logger.debug("Free route error for %s: %s — trying legacy fallback", model_key, _free_err)

        # v9.5: Check circuit breaker before calling
        breaker = self._breakers.get(provider)
        if breaker and not breaker.can_execute():
            logger.warning("Circuit breaker OPEN for %s, skipping to fallback", provider)
            if thinking_agent:
                await thinking_agent.log_resilience_event("CircuitBreaker", f"Circuit breaker OPEN for {provider}", log_level="warning")
            # v25.0 AUTONOMOUS: Try cross-provider, then FreeAccessRouter
            if provider == 'gemini' and self._groq_api_key:
                return await self._call_groq(msgs, FALLBACK_GROQ[0], temperature, max_tokens, thinking_agent=thinking_agent)
            elif provider == 'groq' and self._api_key:
                return await self._call_gemini(msgs, FALLBACK_GEMINI[0], temperature, max_tokens, tools, top_p=top_p, thinking_agent=thinking_agent)
            # AUTONOMOUS: OpenRouter :free works without any key
            return await self._call_openrouter(msgs, temperature=temperature, max_tokens=max_tokens, thinking_agent=thinking_agent)

        for attempt in range(MAX_RETRY + 1):
            try:
                if provider == "gemini":
                    result = await self._call_gemini(
                        msgs, model_id, temperature, max_tokens, tools,
                        top_p=top_p, thinking_agent=thinking_agent,
                    )
                    if breaker: breaker.record_success()
                    return result
                else:
                    result = await self._call_groq(
                        msgs, model_id, temperature, max_tokens, thinking_agent=thinking_agent,
                    )
                    if breaker: breaker.record_success()
                    return result
            except (RateLimitError, OverloadedError) as exc:
                if breaker:
                    breaker.record_failure()
                    try:
                        from arki_project.utils.circuit_breaker import save_breaker_state
                        save_breaker_state()
                    except Exception as _err:
                        logger.warning("Suppressed error: %s", _err)
                logger.warning(
                    "Model %s attempt %d/%d: %s",
                    model_id, attempt + 1, MAX_RETRY + 1, exc,
                )
                if thinking_agent:
                    await thinking_agent.log_resilience_event("Retry", f"Model {model_id} attempt {attempt + 1}/{MAX_RETRY + 1}: {exc.__class__.__name__}", log_level="warning")
                if attempt < MAX_RETRY:
                    delay = _backoff_delay(attempt)
                    logger.info("Backing off %.1fs…", delay)
                    if thinking_agent:
                        await thinking_agent.log_resilience_event("Backoff", f"Backing off {delay:.1f}s", log_level="info")
                    await asyncio.sleep(delay)
                    continue

                # ── Same-provider fallback chain ──
                chain = (
                    FALLBACK_GEMINI
                    if provider == "gemini"
                    else FALLBACK_GROQ
                )
                for fb in chain:
                    if fb == model_id:
                        continue
                    try:
                        logger.info("Fallback → %s (same provider)", fb)
                        if provider == "gemini":
                            return await self._call_gemini(
                                msgs, fb, temperature, max_tokens, tools,
                                top_p=top_p, thinking_agent=thinking_agent,
                            )
                        else:
                            return await self._call_groq(
                                msgs, fb, temperature, max_tokens, thinking_agent=thinking_agent,
                            )
                    except Exception as fb_exc:
                        logger.warning("Same-provider fallback to %s failed: %s", fb, fb_exc)
                        if thinking_agent:
                            await thinking_agent.log_resilience_event("FallbackError", f"Same-provider fallback to {fb} failed: {fb_exc.__class__.__name__}", log_level="error")
                        continue

                # ── Cross-provider fallback ──
                try:
                    if provider == "gemini" and self._groq_api_key:
                        logger.info("Cross-fallback → Groq")
                        return await self._call_groq(
                            msgs, FALLBACK_GROQ[0],
                            temperature, max_tokens, thinking_agent=thinking_agent,
                        )
                    if provider == "groq" and self._api_key:
                        logger.info("Cross-fallback → Gemini")
                        return await self._call_gemini(
                            msgs, FALLBACK_GEMINI[0],
                            temperature, max_tokens, tools,
                            top_p=top_p, thinking_agent=thinking_agent,
                        )
                except Exception as e:
                    logger.debug("Suppressed: %s", e)
                    if thinking_agent:
                        await thinking_agent.log_resilience_event("FallbackError", f"Cross-provider fallback failed: {e.__class__.__name__}", log_level="error")

                # ── OpenRouter universal fallback ──
                try:
                    logger.info("Universal fallback → OpenRouter")
                    return await self._call_openrouter(
                        msgs, temperature=temperature, max_tokens=max_tokens, thinking_agent=thinking_agent,
                    )
                except Exception as or_exc:
                    logger.warning("OpenRouter fallback failed: %s", or_exc)
                    if thinking_agent:
                        await thinking_agent.log_resilience_event("FallbackError", f"OpenRouter fallback failed: {or_exc.__class__.__name__}", log_level="error")

                if thinking_agent:
                    await thinking_agent.log_resilience_event("Critical", "همه مدل‌ها مشغول‌اند. چند دقیقه بعد دوباره تلاش کن.", log_level="critical")
                raise Exception(
                    "⏳ همه مدل‌ها مشغول‌اند. چند دقیقه بعد دوباره تلاش کن.",
                )

        # Should never reach here, but just in case:
        if thinking_agent:
            await thinking_agent.log_resilience_event("Critical", "خطای غیرمنتظره. دوباره تلاش کن.", log_level="critical")
        raise Exception("⏳ خطای غیرمنتظره. دوباره تلاش کن.")

    # ─────── History persistence ───────

    async def _ensure_loaded(self, user_id: int) -> None:
        if user_id in self._loaded_users:
            return
        async with get_session() as session:
            result = await session.execute(
                select(DBChatMessage)
                .where(DBChatMessage.user_id == user_id)
                .order_by(DBChatMessage.created_at.desc())
                .limit(self._max_history),
            )
            rows = result.scalars().all()
        for row in reversed(rows):
            self._history[user_id].append(
                ChatMessage(role=row.role, content=row.content),
            )
        self._loaded_users.add(user_id)

    async def _append(self, user_id: int, role: str, content: str) -> None:
        self._history[user_id].append(ChatMessage(role=role, content=content))
        # Trim in-memory (keep max_history entries).
        if len(self._history[user_id]) > self._max_history * 2:
            self._history[user_id] = self._history[user_id][
                -self._max_history:
            ]
        # Persist to DB.
        async with get_session() as session:
            session.add(
                DBChatMessage(
                    user_id=user_id, role=role, content=content,
                ),
            )
            await session.flush()

    def evict_stale_users(self, max_age_seconds: int = 3600) -> int:
        """Remove in-memory history for users inactive for > max_age_seconds.
        Also enforces MAX_CACHED_USERS hard limit.
        Returns the number of evicted users. Call periodically from a background task."""
        now = time.time()
        evicted = 0

        # 1. Evict stale users (inactive > max_age_seconds)
        stale = [
            uid for uid, msgs in self._history.items()
            if msgs and (now - msgs[-1].timestamp) > max_age_seconds
        ]
        for uid in stale:
            del self._history[uid]
            self._loaded_users.discard(uid)
            evicted += 1

        # 2. Enforce hard limit — evict oldest if over MAX_CACHED_USERS
        if len(self._history) > MAX_CACHED_USERS:
            sorted_users = sorted(
                self._history.items(),
                key=lambda x: x[1][-1].timestamp if x[1] else 0,
            )
            excess = len(self._history) - MAX_CACHED_USERS
            for uid, _ in sorted_users[:excess]:
                del self._history[uid]
                self._loaded_users.discard(uid)
                evicted += 1

        return evicted


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
                                    except Exception as _e:
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
                except Exception as _e:
                    logger.debug("Suppressed: %s", _e)  # v10.1: no longer silent

            return accumulated or await self.ask_raw(
                messages, mk, temperature=temperature, max_tokens=max_tokens,
            )


        except Exception:
            # Fallback to normal (non-streaming)
            return await self.ask_raw(messages, mk, temperature=temperature, max_tokens=max_tokens)




