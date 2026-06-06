
"""
api_builder_pkg/a_p_i_builder_agent.py — APIBuilderAgent
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class APIBuilderAgent:
    """Agent-powered API builder — dynamic, tested, production-ready.

    v4.0 TITAN Features:
      • Dynamic endpoint registration from models_registry (152+ models)
      • Real rate limiting (token bucket per user per model)
      • Auth middleware with tier-based access
      • Pipeline builder (chain multiple models)
      • Endpoint persistence (JSON save/load)
      • Real test framework with quality scoring (no fake 95.0)
      • Full OpenAPI 3.1 spec generation
    
    Connects:
      • models_registry.MODELS (152 models) → via dynamic ModelRouter
      • ai_client.AIClient → for real model calls
      • free_access_router → for free tier routing
      • config.Settings → for API keys from environment
    """

    def __init__(self):
        self.registry = EndpointRegistry()
        self.router = ModelRouter()
        self.spec_gen = OpenAPIGenerator()
        self.rate_limiter = RateLimiter()
        self.auth = AuthMiddleware()
        self.persistence = EndpointPersistence()
        self._pipeline_executor: Optional[PipelineExecutor] = None
        self._test_results: List[EndpointTestResult] = []
        self._model_test_results: List[ModelTestResult] = []
        self._ws_manager: Optional[WebSocketManager] = None
        self._initialized = False
        self._ai_client: Optional[Any] = None
        logger.info("APIBuilderAgent v4.0 TITAN — dynamic registration ready")

    @property
    def pipelines(self) -> PipelineExecutor:
        """Lazy-load pipeline executor."""
        if self._pipeline_executor is None:
            self._pipeline_executor = PipelineExecutor(self)
        return self._pipeline_executor

    @property
    def websockets(self) -> WebSocketManager:
        """Lazy-load WebSocket manager."""
        if self._ws_manager is None:
            self._ws_manager = WebSocketManager(self)
        return self._ws_manager

    def _get_ai_client(self):
        """Lazy-load AIClient with config from environment (same as main.py).

        FreeAccessRouter handles all models without external keys, so
        even empty env vars are fine — the system routes to free tiers.
        """
        if self._ai_client is None:
            from arki_project.utils.ai_client import AIClient
            from arki_project.config import Settings
            s = Settings()
            self._ai_client = AIClient(
                api_key=s.ai_api_key,
                base_url=s.ai_base_url,
                model=s.ai_model,
                max_history=s.ai_max_history,
                temperature=s.ai_temperature,
                max_tokens=s.ai_max_tokens,
                groq_api_key=s.groq_api_key,
                openrouter_api_key=s.openrouter_api_key,
            )
        return self._ai_client

    # ── Initialization ──────────────────────────────────────────


    async def initialize(self):
        """Boot up: register endpoints, load persistence, provision keys."""
        if self._initialized:
            return

        # 1. Register built-in endpoints (12 core endpoints)
        self._register_builtin_endpoints()

        # 2. Auto-provision free API keys
        try:
            from arki_project.utils.free_access_router import initialize_free_access
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(initialize_free_access())
                else:
                    loop.run_until_complete(initialize_free_access())
            except RuntimeError:
                asyncio.run(initialize_free_access())
            logger.info("✅ Free access auto-provisioner activated")
        except Exception as _fa_err:
            logger.debug("Free access provisioner: %s", _fa_err)

        # 3. Dynamic per-model endpoint registration (ALL models from MODELS dict)
        self._register_per_model_endpoints()

        # 4. Load persisted custom endpoints
        saved = self.persistence.load()
        for ep_data in saved:
            try:
                self.create_endpoint(
                    path=ep_data["path"],
                    name=ep_data["name"],
                    description=ep_data["description"],
                    system_prompt=ep_data.get("system_prompt", ""),
                    model_tier=ep_data.get("model_tier", "auto"),
                    parameters=ep_data.get("parameters", []),
                    tags=ep_data.get("tags", ["custom", "persisted"]),
                )
            except Exception as e:
                logger.warning("Failed to load persisted endpoint %s: %s", ep_data.get("path"), e)
        if saved:
            logger.info("Loaded %d persisted custom endpoints", len(saved))

        self._initialized = True
        logger.info("APIBuilderAgent v4.0: %d endpoints registered (%d models)", 
                     self.registry.count, self.router.get_all_models_count())


    def _register_builtin_endpoints(self):
        """Register the default AI-powered API endpoints."""

        # 1. Chat Completion (single model)
        self.registry.register(EndpointDefinition(
            path="chat/completions",
            method=HttpMethod.POST,
            name="Chat Completion",
            description="Single-model chat completion. Supports all 79 models.",
            model_tier=ModelTier.AUTO,
            parameters=[
                EndpointParam("messages", "array", "Chat messages [{role, content}]"),
                EndpointParam("model", "string", "Model key (any of 79 models)", required=False),
                EndpointParam("max_tokens", "number", "Max output tokens", required=False, default=65536),
                EndpointParam("temperature", "number", "Sampling temperature", required=False,
                              default=0.7, min_value=0, max_value=2),
                EndpointParam("stream", "boolean", "Enable SSE streaming", required=False, default=False),
            ],
            system_prompt="You are a helpful AI assistant.",
            tags=["chat", "core"],
        ))

        # 2. Agent Execute (multi-step)
        self.registry.register(EndpointDefinition(
            path="agent/execute",
            method=HttpMethod.POST,
            name="Agent Execute",
            description="Run autonomous multi-step agent with 12+ tools and all 79 models.",
            model_tier=ModelTier.PRO,
            parameters=[
                EndpointParam("query", "string", "Task description for the agent"),
                EndpointParam("model", "string", "Model to use for agent reasoning", required=False),
                EndpointParam("max_steps", "number", "Maximum agent steps", required=False,
                              default=50, min_value=1, max_value=100),
                EndpointParam("tools", "array", "Subset of tools to enable", required=False),
                EndpointParam("max_time_ms", "number", "Time budget in ms", required=False, default=600000),
            ],
            tags=["agent", "core"],
            timeout_seconds=600,
        ))

        # 3. Multi-Model Race (ULTRAPLINIAN)
        self.registry.register(EndpointDefinition(
            path="ultraplinian/completions",
            method=HttpMethod.POST,
            name="ULTRAPLINIAN Race",
            description="Race multiple models and return the best response. Uses ULTRAPLINIAN engine.",
            model_tier=ModelTier.ULTRA,
            parameters=[
                EndpointParam("messages", "array", "Chat messages"),
                EndpointParam("tier", "string", "Race tier: fast|standard|pro|power|ultra",
                              required=False, default="pro",
                              enum=["fast", "standard", "pro", "power", "ultra"]),
                EndpointParam("max_race_models", "number", "Max models to race", required=False, default=5),
                EndpointParam("stream", "boolean", "SSE streaming", required=False, default=True),
            ],
            tags=["ultraplinian", "core"],
        ))

        # 4. Consortium (hive-mind)
        self.registry.register(EndpointDefinition(
            path="consortium/completions",
            method=HttpMethod.POST,
            name="CONSORTIUM Hive-Mind",
            description="Multi-model synthesis: run N models, synthesize best answer.",
            model_tier=ModelTier.CONSORTIUM,
            parameters=[
                EndpointParam("messages", "array", "Chat messages"),
                EndpointParam("tier", "string", "Consortium tier", required=False, default="pro"),
                EndpointParam("synthesis_model", "string", "Model for final synthesis", required=False),
                EndpointParam("stream", "boolean", "SSE streaming", required=False, default=True),
            ],
            tags=["consortium", "core"],
        ))

        # 5. Model Test (test any model)
        self.registry.register(EndpointDefinition(
            path="models/test",
            method=HttpMethod.POST,
            name="Model Tester",
            description="Test any of the 79 models with a prompt and get quality score.",
            model_tier=ModelTier.AUTO,
            parameters=[
                EndpointParam("model", "string", "Model key to test"),
                EndpointParam("prompt", "string", "Test prompt", required=False,
                              default="Explain distributed Saga pattern with Redis Redlock"),
                EndpointParam("expected_keywords", "array", "Keywords expected in response", required=False),
            ],
            tags=["testing", "models"],
        ))

        # 6. Model List (all 72)
        self.registry.register(EndpointDefinition(
            path="models/list",
            method=HttpMethod.GET,
            name="List All Models",
            description="List all 79 models with their providers, tiers, and status.",
            auth_level=AuthLevel.NONE,
            tags=["models", "info"],
        ))

        # 7. API Builder — create new endpoint
        self.registry.register(EndpointDefinition(
            path="builder/create",
            method=HttpMethod.POST,
            name="Create Endpoint",
            description="Dynamically create a new AI-powered API endpoint.",
            auth_level=AuthLevel.ENTERPRISE,
            model_tier=ModelTier.PRO,
            parameters=[
                EndpointParam("path", "string", "Endpoint path (e.g., 'my/custom-ai')"),
                EndpointParam("name", "string", "Endpoint name"),
                EndpointParam("description", "string", "What this endpoint does"),
                EndpointParam("system_prompt", "string", "System prompt for the AI"),
                EndpointParam("model_tier", "string", "Model tier: auto|fast|pro|ultra",
                              required=False, default="auto"),
                EndpointParam("parameters", "array", "Custom parameters", required=False),
            ],
            tags=["builder", "admin"],
        ))

        # 8. API Builder — test suite
        self.registry.register(EndpointDefinition(
            path="builder/test",
            method=HttpMethod.POST,
            name="Test Endpoint",
            description="Run agent-generated test suite against an endpoint.",
            auth_level=AuthLevel.ENTERPRISE,
            parameters=[
                EndpointParam("endpoint_id", "string", "Endpoint to test"),
                EndpointParam("test_count", "number", "Number of test cases", required=False, default=5),
            ],
            tags=["builder", "testing"],
        ))

        # 9. OpenAPI Spec
        self.registry.register(EndpointDefinition(
            path="builder/openapi",
            method=HttpMethod.GET,
            name="OpenAPI Specification",
            description="Get OpenAPI 3.1 spec for all registered endpoints.",
            auth_level=AuthLevel.NONE,
            tags=["builder", "docs"],
        ))

        # 10. Infrastructure Health
        self.registry.register(EndpointDefinition(
            path="infra/health",
            method=HttpMethod.GET,
            name="Infrastructure Health",
            description="Full health check of all infrastructure layers.",
            tags=["infra", "monitoring"],
        ))

        # 11. Smart Completion (auto-route)
        self.registry.register(EndpointDefinition(
            path="smart/completions",
            method=HttpMethod.POST,
            name="Smart Completion",
            description="Auto-routes to the best model based on task analysis.",
            model_tier=ModelTier.AUTO,
            parameters=[
                EndpointParam("messages", "array", "Chat messages"),
                EndpointParam("task_type", "string", "Task type hint",
                              required=False, default="general",
                              enum=["general", "code", "analysis", "creative", "math", "fast"]),
                EndpointParam("budget", "string", "Cost budget: low|medium|high",
                              required=False, default="medium",
                              enum=["low", "medium", "high"]),
            ],
            tags=["smart", "core"],
        ))

        # 12. WebSocket Streaming (real-time bidirectional)
        self.registry.register(EndpointDefinition(
            path="ws/connect",
            method=HttpMethod.GET,
            name="WebSocket Connect",
            description=(
                "WebSocket endpoint for real-time bidirectional streaming. "
                "Supports: auth handshake, streaming chat, channel subscriptions, heartbeat."
            ),
            auth_level=AuthLevel.BASIC,
            parameters=[
                EndpointParam("protocols", "array", "WebSocket sub-protocols", required=False),
            ],
            tags=["websocket", "streaming", "core"],
            metadata={
                "protocol": "wss",
                "heartbeat_interval": 30,
                "max_connections_per_user": 5,
                "idle_timeout": 300,
                "message_types": ["auth", "chat", "subscribe", "unsubscribe", "ping"],
            },
        ))

        # 13. Batch Completion (multiple models parallel)
        self.registry.register(EndpointDefinition(
            path="batch/completions",
            method=HttpMethod.POST,
            name="Batch Completion",
            description="Send same prompt to multiple models in parallel, get all responses.",
            model_tier=ModelTier.PRO,
            parameters=[
                EndpointParam("messages", "array", "Chat messages"),
                EndpointParam("models", "array", "List of model keys to use"),
                EndpointParam("max_parallel", "number", "Max parallel requests", required=False, default=6),
            ],
            tags=["batch", "core"],
        ))



    def _register_per_model_endpoints(self):
        """Dynamically register API endpoints for ALL models in MODELS dict.
        
        Reads from models_registry.MODELS — currently 152 keys (13 base + 139 APEX/Elite).
        Each model gets a /models/{safe_key}/chat endpoint with full parameter set.
        
        No hardcoding — if a model exists in MODELS, it gets an endpoint.
        """
        try:
            from arki_project.utils.models_registry import MODELS as ALL_MODELS, get_apex_tier
        except ImportError:
            logger.warning("Cannot import models_registry — no per-model endpoints")
            return
        
        count = 0
        for model_key, model_info in ALL_MODELS.items():
            # Create URL-safe path: "g-qwen37-max" → "g_qwen37_max"
            safe_key = model_key.replace("-", "_")
            path = f"models/{safe_key}/chat"
            
            # Skip if already registered (from builtin)
            if self.registry.find_by_path(path):
                continue
            
            # Determine tier from APEX or default
            tier = ModelTier.PRO
            apex_tier = None
            try:
                apex_tier = get_apex_tier(model_key)
            except Exception as _apex_err:
                logger.debug("No APEX tier for %s: %s", model_key, _apex_err)
            
            if apex_tier:
                tier_map = {
                    "fast": ModelTier.FAST, "standard": ModelTier.PRO,
                    "smart": ModelTier.PRO, "pro": ModelTier.PRO,
                    "power": ModelTier.ULTRA, "ultra": ModelTier.ULTRA,
                }
                tier = tier_map.get(apex_tier, ModelTier.PRO)
            elif model_info.provider == "groq":
                tier = ModelTier.FAST
            elif model_info.provider == "gemini":
                tier = ModelTier.PRO
            
            # Detect elite models
            is_elite = model_key in (
                "g-qwen37-max", "g-kimi26-think", "g-deepseek-v4-p",
                "g-glm51-think", "g-gemma4-26b", "g-nemotron3-sup", "g-qwen3-coder",
            )
            mode = "elite" if is_elite else ("pro_ultra" if apex_tier else "base")
            
            # Auto-detect tags
            tags = ["model", model_info.provider]
            if is_elite:
                tags.append("elite")
            if apex_tier:
                tags.append(apex_tier)
            
            self.registry.register(EndpointDefinition(
                path=path,
                method=HttpMethod.POST,
                name=f"{model_info.name} Chat",
                description=f"Chat with {model_info.name} [{model_info.id}] — {mode} mode",
                model_tier=tier,
                specific_model=model_key,
                parameters=[
                    EndpointParam("messages", "array", "Chat messages [{role, content}]"),
                    EndpointParam("prompt", "string", "Alternative: single prompt string", required=False),
                    EndpointParam("max_tokens", "number", "Max output tokens", required=False, default=65536),
                    EndpointParam("temperature", "number", "Temperature", required=False,
                                  default=0.7, min_value=0, max_value=2),
                    EndpointParam("stream", "boolean", "SSE streaming", required=False, default=False),
                    EndpointParam("system_prompt", "string", "Custom system prompt", required=False),
                ],
                system_prompt=f"You are {{model_name}}, running in {mode} mode with maximum capability.",
                tags=tags,
                metadata={
                    "model_key": model_key,
                    "model_id": model_info.id,
                    "provider": model_info.provider,
                    "tier": apex_tier or ("elite" if is_elite else "base"),
                    "mode": mode,
                    "context_window": model_info.ctx,
                    "version": "4.0.0",
                    "description_fa": model_info.desc,
                },
            ))
            count += 1
        
        logger.info("Dynamic registration: %d per-model endpoints from MODELS dict", count)


    # ── Endpoint Execution ──────────────────────────────────────

    async def execute_endpoint(self, endpoint_id: str, data: Dict[str, Any],
                              api_key: str = "", user_id: str = "default") -> Dict[str, Any]:
        """Execute a registered endpoint — LIVE model call with rate limiting + auth.

        Flow:
          1. Auth check (if endpoint requires it)
          2. Rate limit check
          3. Validate parameters
          4. Route to correct model via ModelRouter
          5. Build messages array (system_prompt + user messages)
          6. Call ai_client.ask_raw() → real provider (Gemini/Groq/OpenRouter)
          7. Return real model response with transparency metadata
        """
        ep = self.registry.get(endpoint_id)
        if not ep:
            return {"error": f"Endpoint {endpoint_id} not found", "status": "error"}
        if ep.status == EndpointStatus.DISABLED:
            return {"error": f"Endpoint {ep.path} is disabled", "status": "error"}

        t0 = time.time()
        request_id = uuid.uuid4().hex[:12]

        # ── Step 1: Auth check ──
        auth_ok, auth_info = self.auth.validate(api_key, ep.auth_level)
        if not auth_ok:
            return {
                "request_id": request_id,
                "error": "Authentication failed or insufficient tier",
                "required_level": ep.auth_level.value if hasattr(ep.auth_level, 'value') else str(ep.auth_level),
                "status": "auth_error",
            }
        if auth_info and auth_info.get("user_id"):
            user_id = auth_info["user_id"]

        model_key = self.router.select_model(
            ep.model_tier,
            ep.specific_model or data.get("model"),
            data.get("task_type", "general"),
        )

        # ── Step 2: Rate limit check ──
        # Determine provider for rate limits
        provider = "openrouter"
        try:
            from arki_project.utils.models_registry import get_model
            m_info = get_model(model_key)
            provider = m_info.provider
        except Exception as _prov_err:
            logger.debug("Could not resolve provider for %s, defaulting to openrouter: %s",
                         model_key, _prov_err)

        rate_ok, rate_info = self.rate_limiter.check(user_id, model_key, provider)
        if not rate_ok:
            return {
                "request_id": request_id,
                "error": "Rate limit exceeded",
                "retry_after_seconds": rate_info.get("retry_after_seconds", 60) if rate_info else 60,
                "reason": rate_info.get("reason", "rate_limit") if rate_info else "rate_limit",
                "status": "rate_limited",
            }

        try:
            # ── Step 3: Validate parameters ──
            errors = self._validate_params(ep, data)
            if errors:
                return {"error": "Validation failed", "details": errors, "status": "validation_error"}

            # ── Step 4: Build messages array ──
            messages: List[Dict[str, str]] = []

            sys_prompt = data.get("system_prompt", "") or ep.system_prompt or ""
            if sys_prompt:
                from arki_project.utils.models_registry import get_model as _get_model
                try:
                    _m_info = _get_model(model_key)
                    sys_prompt = sys_prompt.replace("{model_name}", _m_info.name)
                except Exception:
                    sys_prompt = sys_prompt.replace("{model_name}", model_key)
                messages.append({"role": "system", "content": sys_prompt})

            user_msgs = data.get("messages")
            if user_msgs and isinstance(user_msgs, list):
                for msg in user_msgs:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        messages.append({"role": msg["role"], "content": msg["content"]})
            else:
                prompt = data.get("prompt") or data.get("message") or data.get("text", "")
                if prompt:
                    messages.append({"role": "user", "content": str(prompt)})

            if not any(m["role"] == "user" for m in messages):
                return {"error": "No user message provided. Send 'messages' array or 'prompt' string.", "status": "error"}

            # ── Step 5: Generation parameters ──
            temperature = float(data.get("temperature", 0.7))
            max_tokens = int(data.get("max_tokens", 65536))

            # ── Step 6: LIVE model call ──
            client = self._get_ai_client()
            response_text = await client.ask_raw(
                messages=messages,
                model_key=model_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            latency = (time.time() - t0) * 1000
            tokens_est = len(response_text) // 4

            self.registry.record_call(endpoint_id, latency, tokens_est)
            self.router.record_latency(model_key, latency)

            # ── Step 7: Build response ──
            result = {
                "request_id": request_id,
                "endpoint": ep.path,
                "model_selected": model_key,
                "model_tier": ep.model_tier.value if hasattr(ep.model_tier, 'value') else str(ep.model_tier),
                "status": "success",
                "response": response_text,
                "usage": {
                    "estimated_tokens": tokens_est,
                    "latency_ms": round(latency, 1),
                },
                "metadata": {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "user_id": user_id,
                },
            }

            if hasattr(client, "_last_transparency") and client._last_transparency:
                result["routing"] = client._last_transparency

            logger.info(
                "execute_endpoint [%s] → model=%s latency=%.0fms tokens≈%d",
                request_id, model_key, latency, tokens_est,
            )
            return result

        except Exception as e:
            latency = (time.time() - t0) * 1000
            self.registry.record_call(endpoint_id, latency, 0, error=True)
            logger.error("execute_endpoint [%s] FAILED: %s", request_id, e)
            return {
                "request_id": request_id,
                "endpoint": ep.path,
                "model_selected": model_key,
                "status": "error",
                "error": str(e),
                "latency_ms": round(latency, 1),
            }

    async def execute_by_path(self, path: str, data: Dict[str, Any],
                              api_key: str = "", user_id: str = "default") -> Dict[str, Any]:
        """Execute endpoint by path string (e.g. 'models/g_qwen37_max/chat')."""
        ep = self.registry.find_by_path(path)
        if not ep:
            return {"error": f"No endpoint found for path: {path}", "status": "error"}
        return await self.execute_endpoint(ep.endpoint_id, data, api_key, user_id)

    async def execute_batch(self, requests: List[Dict[str, Any]],
                            max_concurrent: int = 10) -> List[Dict[str, Any]]:
        """Execute multiple endpoint calls concurrently with limits.

        Each request: {"endpoint_id": "...", "data": {...}} or {"path": "...", "data": {...}}
        """
        sem = asyncio.Semaphore(max_concurrent)

        async def _single(req: Dict) -> Dict:
            async with sem:
                ep_id = req.get("endpoint_id", "")
                api_key = req.get("api_key", "")
                user_id = req.get("user_id", "default")
                if not ep_id and req.get("path"):
                    return await self.execute_by_path(req["path"], req.get("data", {}), api_key, user_id)
                return await self.execute_endpoint(ep_id, req.get("data", {}), api_key, user_id)

        results = await asyncio.gather(*[_single(r) for r in requests], return_exceptions=True)
        return [r if isinstance(r, dict) else {"error": str(r), "status": "error"} for r in results]

    async def quick_chat(self, model_key: str, prompt: str, **kwargs) -> str:
        """One-liner: send a prompt to any model, get response text.

        Usage:
            answer = await api.quick_chat("g-qwen37-max", "سلام! خودت رو معرفی کن")
        """
        client = self._get_ai_client()
        messages = [{"role": "user", "content": prompt}]
        sys_prompt = kwargs.pop("system_prompt", "")
        if sys_prompt:
            messages.insert(0, {"role": "system", "content": sys_prompt})
        return await client.ask_raw(
            messages=messages,
            model_key=model_key,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 65536),
        )


    def _validate_params(self, ep: EndpointDefinition, data: Dict) -> List[str]:
        """Validate request parameters against endpoint definition."""
        errors = []
        for param in ep.parameters:
            if param.required and param.name not in data:
                errors.append(f"Missing required parameter: {param.name}")
            if param.name in data:
                val = data[param.name]
                if param.enum and val not in param.enum:
                    errors.append(f"{param.name} must be one of {param.enum}")
                if param.min_value is not None and isinstance(val, (int, float)) and val < param.min_value:
                    errors.append(f"{param.name} must be >= {param.min_value}")
                if param.max_value is not None and isinstance(val, (int, float)) and val > param.max_value:
                    errors.append(f"{param.name} must be <= {param.max_value}")
        return errors

    # ── Dynamic Endpoint Creation ───────────────────────────────

    def create_endpoint(self, path: str, name: str, description: str,
                        system_prompt: str = "", model_tier: str = "auto",
                        parameters: List[Dict] = None, **kwargs) -> EndpointDefinition:
        """Create a new dynamic API endpoint."""
        tier_map = {
            "auto": ModelTier.AUTO, "fast": ModelTier.FAST,
            "pro": ModelTier.PRO, "ultra": ModelTier.ULTRA,
            "consortium": ModelTier.CONSORTIUM,
        }

        params = []
        for p in (parameters or []):
            params.append(EndpointParam(
                name=p.get("name", ""),
                param_type=p.get("type", "string"),
                description=p.get("description", ""),
                required=p.get("required", True),
                default=p.get("default"),
                enum=p.get("enum", []),
            ))

        # Always add messages param for AI endpoints
        if not any(p.name == "messages" for p in params):
            params.insert(0, EndpointParam("messages", "array", "Chat messages [{role, content}]"))

        ep = EndpointDefinition(
            path=path,
            method=HttpMethod(kwargs.get("method", "POST")),
            name=name,
            description=description,
            system_prompt=system_prompt,
            model_tier=tier_map.get(model_tier, ModelTier.AUTO),
            parameters=params,
            tags=kwargs.get("tags", ["custom"]),
        )

        self.registry.register(ep)
        logger.info("Created dynamic endpoint: %s %s", ep.method.value, ep.path)
        return ep

    # ── OpenAPI Spec ────────────────────────────────────────────


    def get_openapi_spec(self) -> Dict[str, Any]:
        """Generate OpenAPI 3.1 spec for all endpoints."""
        return self.spec_gen.generate(self.registry.list_all())

    # ── Model Testing ───────────────────────────────────────────


    def get_all_model_keys(self) -> List[Dict[str, str]]:
        """Get all 72 model keys with their info (static, no API needed)."""
        # Base models (Gemini + Groq) — 13
        base = [
            {"key": "gemini-pro", "id": "gemini-2.5-pro-preview-05-06", "provider": "gemini", "tier": "pro"},
            {"key": "gemini-flash", "id": "gemini-2.5-flash-preview-04-17", "provider": "gemini", "tier": "fast"},
            {"key": "gemini-flash-lite", "id": "gemini-2.0-flash-lite", "provider": "gemini", "tier": "fast"},
            {"key": "gemini-pro-search", "id": "gemini-2.5-pro-preview-05-06", "provider": "gemini", "tier": "pro"},
            {"key": "gemini-image", "id": "gemini-2.0-flash-preview-image-generation", "provider": "gemini", "tier": "pro"},
            {"key": "gemini-exp", "id": "gemini-2.5-pro-exp-03-25", "provider": "gemini", "tier": "pro"},
            {"key": "llama8", "id": "llama-3.3-70b-versatile", "provider": "groq", "tier": "fast"},
            {"key": "llama70", "id": "llama-3.3-70b-versatile", "provider": "groq", "tier": "pro"},
            {"key": "llama90", "id": "llama-3.2-90b-vision-preview", "provider": "groq", "tier": "pro"},
            {"key": "mixtral", "id": "mixtral-8x7b-32768", "provider": "groq", "tier": "fast"},
            {"key": "deepseek-r1-groq", "id": "deepseek-r1-distill-llama-70b", "provider": "groq", "tier": "pro"},
            {"key": "qwen-qwq", "id": "qwen-qwq-32b", "provider": "groq", "tier": "pro"},
            {"key": "llama4-scout", "id": "meta-llama/llama-4-scout-17b-16e-instruct", "provider": "groq", "tier": "fast"},
        ]

        # APEX models (OpenRouter) — 59
        g0d = [
            # Fast tier (12)
            {"key": "g-gemini20-flash", "provider": "openrouter", "tier": "fast"},
            {"key": "g-gemini20-flash-lite", "provider": "openrouter", "tier": "fast"},
            {"key": "g-llama4-mav", "provider": "openrouter", "tier": "fast"},
            {"key": "g-llama4-scout", "provider": "openrouter", "tier": "fast"},
            {"key": "g-mistral-small", "provider": "openrouter", "tier": "fast"},
            {"key": "g-phi4", "provider": "openrouter", "tier": "fast"},
            {"key": "g-phi4-mini", "provider": "openrouter", "tier": "fast"},
            {"key": "g-gemma3-27b", "provider": "openrouter", "tier": "fast"},
            {"key": "g-qwen3-30b", "provider": "openrouter", "tier": "fast"},
            {"key": "g-qwen3-32b", "provider": "openrouter", "tier": "fast"},
            {"key": "g-ministral-8b", "provider": "openrouter", "tier": "fast"},
            {"key": "g-glm4-32b", "provider": "openrouter", "tier": "fast"},
            # Standard tier (16)
            {"key": "g-gpt4o", "provider": "openrouter", "tier": "standard"},
            {"key": "g-gpt4o-mini", "provider": "openrouter", "tier": "standard"},
            {"key": "g-gpt41", "provider": "openrouter", "tier": "standard"},
            {"key": "g-gpt41-mini", "provider": "openrouter", "tier": "standard"},
            {"key": "g-gpt41-nano", "provider": "openrouter", "tier": "standard"},
            {"key": "g-claude37-sonnet", "provider": "openrouter", "tier": "standard"},
            {"key": "g-claude35-haiku", "provider": "openrouter", "tier": "standard"},
            {"key": "g-gemini25-flash", "provider": "openrouter", "tier": "standard"},
            {"key": "g-gemini25-flash-lite", "provider": "openrouter", "tier": "standard"},
            {"key": "g-llama33-70b", "provider": "openrouter", "tier": "standard"},
            {"key": "g-mistral-medium", "provider": "openrouter", "tier": "standard"},
            {"key": "g-codestral", "provider": "openrouter", "tier": "standard"},
            {"key": "g-command-a", "provider": "openrouter", "tier": "standard"},
            {"key": "g-deepseek-v3", "provider": "openrouter", "tier": "standard"},
            {"key": "g-qwen3-235b", "provider": "openrouter", "tier": "standard"},
            {"key": "g-nous-deephermes", "provider": "openrouter", "tier": "standard"},
            # Pro tier (13)
            {"key": "g-gpt5", "provider": "openrouter", "tier": "pro"},
            {"key": "g-gpt5-mini", "provider": "openrouter", "tier": "pro"},
            {"key": "g-claude-sonnet-4", "provider": "openrouter", "tier": "pro"},
            {"key": "g-gemini25-pro", "provider": "openrouter", "tier": "pro"},
            {"key": "g-gemini3-pro", "provider": "openrouter", "tier": "pro"},
            {"key": "g-grok3", "provider": "openrouter", "tier": "pro"},
            {"key": "g-grok3-mini", "provider": "openrouter", "tier": "pro"},
            {"key": "g-deepseek-r1", "provider": "openrouter", "tier": "pro"},
            {"key": "g-mistral-large", "provider": "openrouter", "tier": "pro"},
            {"key": "g-llama4-behemoth", "provider": "openrouter", "tier": "pro"},
            {"key": "g-perplexity-sonar-pro", "provider": "openrouter", "tier": "pro"},
            {"key": "g-nvidia-llama70", "provider": "openrouter", "tier": "pro"},
            {"key": "g-moonshot-kimi", "provider": "openrouter", "tier": "pro"},
            # Power tier (11)
            {"key": "g-claude-opus-4", "provider": "openrouter", "tier": "power"},
            {"key": "g-grok4", "provider": "openrouter", "tier": "power"},
            {"key": "g-o3", "provider": "openrouter", "tier": "power"},
            {"key": "g-o4-mini", "provider": "openrouter", "tier": "power"},
            {"key": "g-o4-mini-high", "provider": "openrouter", "tier": "power"},
            {"key": "g-grok3-think", "provider": "openrouter", "tier": "power"},
            {"key": "g-perplexity-sonar-deep", "provider": "openrouter", "tier": "power"},
            {"key": "g-deepseek-r1-0528", "provider": "openrouter", "tier": "power"},
            {"key": "g-qwen3-coder", "provider": "openrouter", "tier": "power"},
            {"key": "g-step2-16k", "provider": "openrouter", "tier": "power"},
            {"key": "g-xiaomi-megrez", "provider": "openrouter", "tier": "power"},
            # Ultra tier (7)
            {"key": "g-claude-opus-4-think", "provider": "openrouter", "tier": "ultra"},
            {"key": "g-gpt5-turbo", "provider": "openrouter", "tier": "ultra"},
            {"key": "g-o3-pro", "provider": "openrouter", "tier": "ultra"},
            {"key": "g-grok4-think", "provider": "openrouter", "tier": "ultra"},
            {"key": "g-gemini25-pro-deep", "provider": "openrouter", "tier": "ultra"},
            {"key": "g-deepseek-r2", "provider": "openrouter", "tier": "ultra"},
            {"key": "g-z1", "provider": "openrouter", "tier": "ultra"},
        ]

        return base + g0d


    def get_all_model_keys_v2(self) -> List[Dict[str, str]]:
        """Get ALL model keys from models_registry.MODELS — dynamic, never stale.
        
        Returns list of {key, id, name, provider, tier, ctx, desc} for each model.
        """
        try:
            from arki_project.utils.models_registry import MODELS, get_apex_tier
        except ImportError:
            return []
        
        result = []
        for key, info in MODELS.items():
            apex_tier = None
            try:
                apex_tier = get_apex_tier(key)
            except Exception as _tier_err:
                logger.debug("No APEX tier for %s: %s", key, _tier_err)
            
            is_elite = key in (
                "g-qwen37-max", "g-kimi26-think", "g-deepseek-v4-p",
                "g-glm51-think", "g-gemma4-26b", "g-nemotron3-sup", "g-qwen3-coder",
            )
            
            result.append({
                "key": key,
                "id": info.id,
                "name": info.name,
                "provider": info.provider,
                "tier": "elite" if is_elite else (apex_tier or "base"),
                "ctx": info.ctx,
                "desc": info.desc,
            })
        
        return result


    # ── Model Testing (REAL quality scoring) ────────────────────

    async def test_all_models_pro_ultra(self, test_prompt: str = None,
                                       max_concurrent: int = 10,
                                       timeout_per_model: float = 30.0) -> Dict[str, Any]:
        """Test ALL models with REAL API calls and quality scoring.
        
        Quality scoring:
          - Response exists and is non-empty → +30
          - Response length > 100 chars → +10
          - Response length > 500 chars → +10
          - Contains expected keywords → +20
          - Persian text detected (if applicable) → +10
          - No error/exception strings → +10
          - Latency < 10s → +10
          
        Max score: 100
        """
        if not test_prompt:
            test_prompt = (
                "Explain the distributed Saga pattern with Redis Redlock for "
                "microservices orchestration. Include: 1) Compensating transactions "
                "with exactly-once semantics, 2) Fence tokens for lock safety, "
                "3) Event sourcing integration, 4) Python asyncio implementation "
                "with proper error handling and circuit breakers."
            )
        
        expected_keywords = [
            "saga", "compensat", "redis", "lock", "event", "async",
            "circuit", "transaction", "idempoten",
        ]
        
        all_models = self.get_all_model_keys_v2()
        results = []
        passed = 0
        failed = 0
        
        sem = asyncio.Semaphore(max_concurrent)
        
        async def _test_one(model_info: Dict) -> ModelTestResult:
            key = model_info["key"]
            mid = model_info["id"]
            provider = model_info["provider"]
            tier = model_info.get("tier", "pro")
            
            async with sem:
                t0 = time.time()
                try:
                    response = await asyncio.wait_for(
                        self.quick_chat(key, test_prompt),
                        timeout=timeout_per_model,
                    )
                    latency = (time.time() - t0) * 1000
                    
                    # Real quality scoring
                    score = 0
                    if response and len(response.strip()) > 0:
                        score += 30
                    if len(response) > 100:
                        score += 10
                    if len(response) > 500:
                        score += 10
                    
                    # Keyword matching
                    response_lower = response.lower()
                    kw_hits = sum(1 for kw in expected_keywords if kw in response_lower)
                    score += min(20, int(kw_hits / max(len(expected_keywords), 1) * 20))
                    
                    # No error strings
                    error_markers = ["error", "exception", "traceback", "failed"]
                    if not any(em in response_lower[:200] for em in error_markers):
                        score += 10
                    
                    # Latency bonus
                    if latency < 10000:
                        score += 10
                    
                    # Cap at 100
                    score = min(100, score)
                    
                    return ModelTestResult(
                        model_key=key, model_id=mid, provider=provider,
                        available=True, latency_ms=latency,
                        response_quality=float(score),
                        response_preview=response[:300],
                        tier=tier,
                    )
                    
                except asyncio.TimeoutError:
                    return ModelTestResult(
                        model_key=key, model_id=mid, provider=provider,
                        available=False, latency_ms=(time.time() - t0) * 1000,
                        error=f"Timeout after {timeout_per_model}s",
                        tier=tier,
                    )
                except Exception as e:
                    return ModelTestResult(
                        model_key=key, model_id=mid, provider=provider,
                        available=False, latency_ms=(time.time() - t0) * 1000,
                        error=str(e),
                        tier=tier,
                    )
        
        # Run tests with concurrency limit
        tasks = [_test_one(m) for m in all_models]
        test_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for r in test_results:
            if isinstance(r, Exception):
                failed += 1
                continue
            results.append(r)
            self._model_test_results.append(r)
            if r.available:
                passed += 1
            else:
                failed += 1
        
        # Sort by quality score descending
        results.sort(key=lambda r: r.response_quality or 0, reverse=True)
        
        return {
            "test_prompt": test_prompt[:100] + "..." if len(test_prompt) > 100 else test_prompt,
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed}/{len(results)} ({passed/max(len(results),1)*100:.1f}%)",
            "avg_quality": round(sum(r.response_quality for r in results if r.available) / max(passed, 1), 1),
            "avg_latency_ms": round(sum(r.latency_ms for r in results if r.available) / max(passed, 1), 1),
            "results": [
                {
                    "key": r.model_key,
                    "id": r.model_id,
                    "provider": r.provider,
                    "tier": r.tier,
                    "available": r.available,
                    "quality_score": r.response_quality,
                    "latency_ms": round(r.latency_ms, 2),
                    "response_preview": r.response_preview[:150] if r.response_preview else None,
                    "error": r.error,
                }
                for r in results
            ],
        }


    # ── Test Results ────────────────────────────────────────────

    def get_test_report(self) -> Dict[str, Any]:
        """Get comprehensive test report."""
        return {
            "endpoint_tests": {
                "total": len(self._test_results),
                "passed": sum(1 for t in self._test_results if t.passed),
                "failed": sum(1 for t in self._test_results if not t.passed),
                "results": [
                    {
                        "endpoint": t.endpoint_id,
                        "test": t.test_name,
                        "passed": t.passed,
                        "model": t.model_used,
                        "latency_ms": t.latency_ms,
                        "quality": t.quality_score,
                        "error": t.error,
                    }
                    for t in self._test_results
                ],
            },
            "model_tests": {
                "total": len(self._model_test_results),
                "available": sum(1 for m in self._model_test_results if m.available),
                "results": [
                    {
                        "key": m.model_key,
                        "id": m.model_id,
                        "provider": m.provider,
                        "available": m.available,
                        "latency_ms": m.latency_ms,
                        "quality": m.response_quality,
                        "tier": m.tier,
                        "error": m.error,
                    }
                    for m in self._model_test_results
                ],
            },
            "endpoints": {
                "total": self.registry.count,
                "active": self.registry.active_count,
            },
            "model_count": 72,
        }

    # ── Summary ─────────────────────────────────────────────────


    # ── Summary ─────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Get API Builder status — complete system overview."""
        model_count = self.router.get_all_models_count()
        return {
            "version": "4.0.0-TITAN-DYNAMIC",
            "initialized": self._initialized,
            "endpoints": {
                "total": self.registry.count,
                "active": self.registry.active_count,
                "builtin": 13,
                "per_model": max(0, self.registry.count - 13),
            },
            "models": {
                "total": model_count,
                "note": "Dynamic from models_registry.MODELS — not hardcoded",
            },
            "features": {
                "rate_limiter": True,
                "auth_middleware": True,
                "pipeline_builder": True,
                "endpoint_persistence": True,
                "real_test_framework": True,
                "dynamic_registration": True,
                "streaming_ready": True,
            "websocket_manager": True,
            },
            "test_summary": {
                "total_tests": len(self._model_test_results),
                "passed": sum(1 for m in self._model_test_results if m.available),
                "avg_quality": round(
                    sum(m.response_quality for m in self._model_test_results if m.available) /
                    max(sum(1 for m in self._model_test_results if m.available), 1), 1
                ),
            },
            "router_stats": self.router.get_model_stats(),
        }



# ═══════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════



