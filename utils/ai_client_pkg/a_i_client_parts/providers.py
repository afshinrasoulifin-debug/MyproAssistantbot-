
"""
AIClient — Providers mixin
"""
from __future__ import annotations

class AIClientProvidersMixin:
    """Methods related to providers."""

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
                except ProviderRateLimitError as _err:
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
            except ProviderAuthError:
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
            except AIProviderError as _err:
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

    async def _call_claude_ultra(
        self,
        msgs: list[dict],
        model_id: str = "claude-sonnet-4-20250514",
        temperature: float = 0.7,
        max_tokens: int = 65536,
        *,
        thinking_agent: ThinkingAgentPro | None = None,
        **_: object,
    ) -> str:
        """
        Claude Ultra — calls free-claude-code proxy (Anthropic Messages API).

        The proxy routes to free providers (NVIDIA NIM, OpenRouter, Gemini, etc.)
        while exposing a standard Anthropic Messages API interface.

        Proxy must be running at CLAUDE_ULTRA_BASE_URL (default: http://localhost:8082).
        """
        import logging as _logging
        import os as _os
        from arki_project.utils.ai_client_pkg.rate_limit_error import RateLimitError as _RLE
        from arki_project.utils.ai_client_pkg.overloaded_error import OverloadedError as _OLE

        _log = _logging.getLogger("arki.claude_ultra")

        base_url = _os.environ.get("CLAUDE_ULTRA_BASE_URL", "http://localhost:8082")
        auth_token = _os.environ.get("CLAUDE_ULTRA_AUTH_TOKEN", "freecc")

        # ── Convert messages to Anthropic format ──
        system_text = ""
        anthropic_msgs: list[dict] = []
        for m in msgs:
            role = m.get("role", "")
            content = m.get("content", "")
            if role == "system":
                system_text = content
            elif role in ("user", "assistant"):
                anthropic_msgs.append({"role": role, "content": content})

        if not anthropic_msgs:
            raise Exception("Claude Ultra: پیامی برای ارسال وجود ندارد")

        body: dict = {
            "model": model_id,
            "messages": anthropic_msgs,
            "max_tokens": min(max_tokens, 8192),
            "temperature": temperature,
            "stream": False,
        }
        if system_text:
            body["system"] = system_text

        headers = {
            "Content-Type": "application/json",
            "x-api-key": auth_token,
            "anthropic-version": "2023-06-01",
        }

        url = f"{base_url.rstrip('/')}/v1/messages"

        # ── HTTP call via shared pool (same pattern as _call_gemini) ──
        client = await self._get_pool_client("claude_ultra")
        try:
            async with client.post(url, json=body, headers=headers) as resp:
                status = resp.status          # aiohttp: .status
                data = await resp.json()      # aiohttp: await .json()
        except Exception as conn_err:
            _log.warning("Claude Ultra connection error: %s", conn_err)
            if thinking_agent:
                await thinking_agent.log_resilience_event(
                    "ConnectionError",
                    f"Claude Ultra proxy unreachable: {conn_err}",
                    log_level="error",
                )
            raise Exception(
                f"❌ پروکسی Claude Ultra در دسترس نیست ({base_url}). "
                "مطمئن شو free-claude-code سرور ران هست."
            ) from conn_err

        # ── Error handling (same pattern as _call_gemini/_call_groq) ──
        if status == 429:
            if thinking_agent:
                await thinking_agent.log_resilience_event(
                    "RateLimit", "Claude Ultra 429", log_level="error",
                )
            raise _RLE("claude_ultra 429")

        if status in (500, 502, 503):
            if thinking_agent:
                await thinking_agent.log_resilience_event(
                    "Overloaded", f"Claude Ultra HTTP {status}", log_level="error",
                )
            raise _OLE(f"claude_ultra HTTP {status}")

        if status != 200:
            err_msg = ""
            if isinstance(data, dict):
                err_obj = data.get("error", {})
                if isinstance(err_obj, dict):
                    err_msg = err_obj.get("message", "")
                elif isinstance(err_obj, str):
                    err_msg = err_obj
            if not err_msg:
                err_msg = f"HTTP {status}"
            raise Exception(f"Claude Ultra: {err_msg}")

        # ── Parse Anthropic Messages response format ──
        content_blocks = data.get("content", [])
        if not content_blocks:
            raise Exception("Claude Ultra: پاسخی دریافت نشد")

        parts: list[str] = []
        for block in content_blocks:
            if isinstance(block, dict):
                btype = block.get("type", "")
                if btype == "text":
                    txt = block.get("text", "")
                    if txt:
                        parts.append(txt)
                elif btype == "thinking":
                    think_text = block.get("thinking", "")
                    if think_text:
                        parts.append(f"💭 *تفکر:*\n{think_text}\n\n")
            elif isinstance(block, str):
                parts.append(block)

        result = "".join(parts).strip()
        if not result:
            raise Exception("Claude Ultra: پاسخ خالی")

        _log.info(
            "🟣 Claude Ultra → %s (tokens: in=%s out=%s)",
            model_id,
            data.get("usage", {}).get("input_tokens", "?"),
            data.get("usage", {}).get("output_tokens", "?"),
        )
        return result

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
        except AIProviderError as _ti_err:
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
        except AIProviderError as _orch_err:
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
        except AIProviderError as _mw_err:
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
            except AIProviderError as _or_err:
                logger.warning("Direct OpenRouter %s failed: %s — falling to free router", model_id, _or_err)

        # ── Claude Ultra: Direct call to free-claude-code proxy ──
        if provider == "claude_ultra":
            try:
                result = await self._call_claude_ultra(
                    msgs, model_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    thinking_agent=thinking_agent,
                )
                self._last_transparency = {
                    "actual_model": model_id,
                    "actual_key": model_key,
                    "was_fallback": False,
                    "requested_key": model_key,
                    "route": "claude_ultra_proxy",
                }
                logger.info("🟣 Claude Ultra → %s (%s)", model_key, model_id)
                if _METRICS:
                    record_request(provider, model_id, "claude_ultra_success", 0.0)
                return result
            except (RateLimitError, OverloadedError) as _cu_err:
                logger.warning("Claude Ultra %s hit %s — falling to free router", model_id, _cu_err)
            except Exception as _cu_err:
                logger.warning("Claude Ultra %s failed: %s — falling to free router", model_id, _cu_err)
                if thinking_agent:
                    await thinking_agent.log_resilience_event(
                        "Error", f"Claude Ultra failed: {_cu_err}", log_level="error"
                    )

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
            except ProviderAuthError as _free_err:
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
                    except AIProviderError as _err:
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
                    except AIProviderError as fb_exc:
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
                except AIProviderError as e:
                    logger.debug("Suppressed: %s", e)
                    if thinking_agent:
                        await thinking_agent.log_resilience_event("FallbackError", f"Cross-provider fallback failed: {e.__class__.__name__}", log_level="error")

                # ── OpenRouter universal fallback ──
                try:
                    logger.info("Universal fallback → OpenRouter")
                    return await self._call_openrouter(
                        msgs, temperature=temperature, max_tokens=max_tokens, thinking_agent=thinking_agent,
                    )
                except AIProviderError as or_exc:
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



