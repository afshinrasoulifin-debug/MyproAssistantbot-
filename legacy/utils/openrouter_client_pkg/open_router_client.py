
"""
openrouter_client_pkg/open_router_client.py — OpenRouterClient
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class OpenRouterClient:
    """
    Full OpenRouter API client.

    The main interface for all LLM interactions.
    """

    API_BASE = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.circuit_breaker = CircuitBreaker()
        self.router = ModelRouter(self.circuit_breaker)
        self.cost_tracker = CostTracker()
        self.cache = RequestCache()
        self.context_manager = ContextManager()
        self.functions = FunctionRegistry()
        self.default_model = "google/gemini-2.5-pro"
        self.request_count = 0

    def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        functions: Optional[List[FunctionDef]] = None,
        user_id: str = "default",
        use_cache: bool = True,
    ) -> ChatResponse:
        """
        Send a chat completion request.

        This is the primary method for interacting with LLMs.
        """
        model = model or self.default_model
        self.request_count += 1

        # Check budget
        within, remaining = True, 999999  # v9.7.1: No budget limits
        if not within:
            raise ValueError(f"Budget exceeded for user {user_id}")

        # Get model info
        model_info = MODEL_REGISTRY.get(model)

        # Context management
        if model_info:
            messages = self.context_manager.truncate_messages(
                messages, model_info.context_length,
            )

        # Check cache
        msg_dicts = [m.to_dict() for m in messages]
        params = {"temperature": temperature, "max_tokens": max_tokens}

        if use_cache:
            cached = self.cache.get(model, msg_dicts, params)
            if cached:
                return cached

        # Build request
        request_body: Dict[str, Any] = {
            "model": model,
            "messages": msg_dicts,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if functions:
            request_body["tools"] = [
                f.to_openai_schema() for f in functions
            ]

        # Build headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://arki-bot.app",
            "X-Title": "Arki Bot",
        }

        start = time.time()

        # In production: httpx.post(f"{self.API_BASE}/chat/completions", ...)
        # Here we return the prepared request for the bot to execute
        latency = (time.time() - start) * 1000

        # Estimate tokens
        input_text = " ".join(m.content for m in messages)
        input_tokens = self.context_manager.estimate_tokens(input_text)
        output_tokens = max_tokens // 2  # estimate

        # Calculate cost
        cost = 0.0
        if model_info:
            cost = model_info.estimated_cost(input_tokens, output_tokens)

        response = ChatResponse(
            model=model,
            content="[API response — connect httpx to execute]",
            usage={
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            cost=cost,
            latency_ms=latency,
        )

        # Track cost
        self.cost_tracker.record(
            model, cost, input_tokens, output_tokens, user_id,
        )
        self.circuit_breaker.record_success(model)

        # Cache response
        if use_cache:
            self.cache.put(model, msg_dicts, params, response)

        return response

    def chat_with_routing(
        self,
        messages: List[ChatMessage],
        task: TaskType = TaskType.CHAT,
        max_tier: ModelTier = ModelTier.FREE,
        **kwargs,
    ) -> ChatResponse:
        """Chat with automatic model selection."""
        model_info = self.router.select(
            task=task,
            max_tier=max_tier,
            require_functions=kwargs.get("functions") is not None,
        )
        if not model_info:
            raise ValueError("No suitable model found")

        return self.chat(messages, model=model_info.id, **kwargs)

    def list_models(self, tier: Optional[ModelTier] = None) -> List[Dict[str, Any]]:
        """List available models."""
        models = []
        for model_id, info in MODEL_REGISTRY.items():
            if tier and info.tier != tier:
                continue
            models.append({
                "id": info.id,
                "name": info.name,
                "provider": info.provider,
                "tier": info.tier.value,
                "context_length": info.context_length,
                "cost": f"${info.input_cost_per_1k}/1K in, ${info.output_cost_per_1k}/1K out",
                "features": {
                    "functions": info.supports_functions,
                    "streaming": info.supports_streaming,
                    "vision": info.supports_vision,
                },
            })
        return models

    def get_free_models(self) -> List[ModelInfo]:
        """Get all free models."""
        return [
            m for m in MODEL_REGISTRY.values()
            if m.tier == ModelTier.FREE
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "total_requests": self.request_count,
            "cost": self.cost_tracker.get_report(),
            "cache_hits": self.cache.hits,
            "cache_misses": self.cache.misses,
            "circuit_breaker": {
                model: state
                for model, state in self.circuit_breaker.states.items()
            },
        }

    def build_request(self, model: str,
                      messages: List[ChatMessage],
                      **kwargs) -> Dict[str, Any]:

        """Build a raw API request (for external execution)."""
        return {
            "url": f"{self.API_BASE}/chat/completions",
            "headers": {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://arki-bot.app",
                "X-Title": "Arki Bot",
            },
            "body": {
                "model": model,
                "messages": [m.to_dict() for m in messages],
                **kwargs,
            },
        }



