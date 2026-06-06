
from __future__ import annotations
"""
tg_bot/utils/internal_api_gateway.py — Internal API Gateway v3.3
═══════════════════════════════════════════════════════════════════
Unified gateway that routes AI requests through internal management:
- Key rotation via APIKeyManager
- Request queueing via RequestQueue
- Circuit breaking per provider
- Response caching
- Cost tracking & budget enforcement
- Health monitoring
"""
import logging, time, json
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Internal imports
from arki_project.utils.api_key_manager import get_key_manager
from arki_project.utils.request_queue import get_request_queue, Priority
from arki_project.utils.circuit_breaker import CircuitBreaker
from arki_project.utils.ai_response_cache import get_ai_cache
from arki_project.utils.http_session_pool import get_http_pool


class InternalAPIGateway:
    """Unified internal gateway for all external API calls."""

    PROVIDER_ENDPOINTS = {
        "openrouter": "https://openrouter.ai/api/v1/chat/completions",
        "groq": "https://api.groq.com/openai/v1/chat/completions",
        "gemini": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "openai": "https://api.openai.com/v1/chat/completions",
        "anthropic": "https://api.anthropic.com/v1/messages",
    }

    def __init__(self) -> None:
        self._key_mgr = get_key_manager()
        self._queue = get_request_queue()
        self._cache = get_ai_cache()
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._cost_tracker: Dict[str, float] = {}
        self._health: Dict[str, Dict] = {}
        self._stats = {
            "total_requests": 0, "cache_hits": 0, "circuit_breaks": 0,
            "total_cost_usd": 0.0, "provider_calls": {},
        }

        # Init circuit breakers per provider
        for provider in self.PROVIDER_ENDPOINTS:
            self._breakers[provider] = CircuitBreaker(
                name=provider, failure_threshold=5, recovery_timeout=60.0
            )

    def _resolve_provider(self, model: str) -> str:
        """Determine provider from model string."""
        model_lower = model.lower()
        if "/" in model:
            prefix = model.split("/")[0].lower()
            provider_map = {
                "google": "gemini", "openai": "openai", "anthropic": "anthropic",
                "meta-llama": "openrouter", "mistralai": "openrouter",
                "deepseek": "openrouter", "qwen": "openrouter",
                "nvidia": "openrouter", "cohere": "openrouter",
            }
            return provider_map.get(prefix, "openrouter")
        if "gemini" in model_lower:
            return "gemini"
        if "gpt" in model_lower or "o1" in model_lower or "o3" in model_lower:
            return "openai"
        if "claude" in model_lower:
            return "anthropic"
        return "openrouter"

    async def request(self, model: str, messages: List[Dict],
                     temperature: float = 0.7, max_tokens: int = 4096,
                     priority: Priority = Priority.NORMAL,
                     use_cache: bool = True, user_id: int = 0) -> Dict[str, Any]:
        """Send AI request through internal gateway."""
        self._stats["total_requests"] += 1
        provider = self._resolve_provider(model)

        # 1. Check cache
        if use_cache and messages:
            prompt_text = messages[-1].get("content", "")
            cached = self._cache.get(prompt_text, model, temperature)
            if cached:
                self._stats["cache_hits"] += 1
                return {"content": cached, "cached": True, "provider": provider, "cost": 0.0}

        # 2. Check circuit breaker
        breaker = self._breakers.get(provider)
        if breaker and breaker.state.value == "open":
            self._stats["circuit_breaks"] += 1
            # Try fallback provider
            fallback = await self._get_fallback_provider(provider)
            if fallback:
                logger.info("Circuit open for %s, falling back to %s", provider, fallback)
                provider = fallback
            else:
                return {"error": f"All providers unavailable", "provider": provider}

        # 3. Get API key
        key = await self._key_mgr.get_key(provider)
        if not key:
            fallback = await self._get_fallback_provider(provider)
            if fallback:
                key = await self._key_mgr.get_key(fallback)
                provider = fallback
            if not key:
                return {"error": "No API keys available", "provider": provider}

        # 4. Make request
        t0 = time.time()
        try:
            result = await self._execute_request(
                provider, model, messages, key, temperature, max_tokens
            )
            duration = time.time() - t0

            # Track success
            if breaker:
                breaker.record_success()
            tokens_used = result.get("usage", {}).get("total_tokens", 0)
            cost = self._estimate_cost(provider, model, tokens_used)
            await self._key_mgr.report_success(provider, key, tokens_used, cost)

            # Cache response
            content = result.get("content", "")
            if use_cache and content and messages:
                self._cache.set(messages[-1].get("content", ""), model, content, temperature)

            # Track stats
            self._stats["total_cost_usd"] += cost
            self._stats["provider_calls"][provider] = self._stats["provider_calls"].get(provider, 0) + 1
            self._update_health(provider, True, duration)

            return {
                "content": content, "provider": provider, "model": model,
                "tokens": tokens_used, "cost": cost, "duration_ms": int(duration * 1000),
                "cached": False,
            }

        except Exception as e:
            duration = time.time() - t0
            is_rate_limit = "429" in str(e) or "rate" in str(e).lower()
            if breaker:
                breaker.record_failure()
            await self._key_mgr.report_error(provider, key, str(e), is_rate_limit)
            self._update_health(provider, False, duration)
            logger.error("Gateway request failed [%s/%s]: %s", provider, model, e)
            return {"error": str(e), "provider": provider, "model": model}

    async def _execute_request(self, provider: str, model: str,
                               messages: List[Dict], key: str,
                               temperature: float, max_tokens: int) -> Dict:
        """Execute HTTP request to provider API."""
        pool = get_http_pool()
        endpoint = self.PROVIDER_ENDPOINTS.get(provider, self.PROVIDER_ENDPOINTS["openrouter"])

        if provider == "gemini":
            endpoint = endpoint.format(model=model.split("/")[-1] if "/" in model else model)
            headers = {"Content-Type": "application/json"}
            body = {
                "contents": [{"parts": [{"text": m["content"]}] } for m in messages if m.get("content")],
                "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
            }
            url = f"{endpoint}?key={key}"
        elif provider == "anthropic":
            headers = {
                "x-api-key": key, "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            system_msg = ""
            chat_msgs = []
            for m in messages:
                if m.get("role") == "system":
                    system_msg = m["content"]
                else:
                    chat_msgs.append(m)
            body = {"model": model, "messages": chat_msgs, "max_tokens": max_tokens,
                    "temperature": temperature}
            if system_msg:
                body["system"] = system_msg
            url = endpoint
        else:
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            if provider == "openrouter":
                headers["HTTP-Referer"] = "https://arki-bot.com"
                headers["X-Title"] = "Arki AI Bot"
            body = {"model": model, "messages": messages,
                    "temperature": temperature, "max_tokens": max_tokens}
            url = endpoint

        resp = await pool.post(url, json=body, headers=headers, session_name=f"ai_{provider}")
        async with resp:
            data = await resp.json()
            if resp.status != 200:
                raise Exception(f"API {resp.status}: {json.dumps(data)[:300]}")

            # Normalize response
            content = ""
            usage = {}
            if provider == "gemini":
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    content = parts[0].get("text", "") if parts else ""
                usage = data.get("usageMetadata", {})
            elif provider == "anthropic":
                content_blocks = data.get("content", [])
                content = content_blocks[0].get("text", "") if content_blocks else ""
                usage = data.get("usage", {})
            else:
                choices = data.get("choices", [])
                content = choices[0].get("message", {}).get("content", "") if choices else ""
                usage = data.get("usage", {})

            return {"content": content, "usage": usage, "raw": data}

    async def _get_fallback_provider(self, failed: str) -> Optional[str]:
        """Get best fallback provider."""
        fallback_order = {
            "gemini": ["openrouter", "groq"],
            "openai": ["openrouter", "groq"],
            "anthropic": ["openrouter", "groq"],
            "groq": ["openrouter", "gemini"],
            "openrouter": ["groq", "gemini"],
        }
        for alt in fallback_order.get(failed, ["openrouter"]):
            breaker = self._breakers.get(alt)
            if breaker and breaker.state.value != "open":
                key = await self._key_mgr.get_key(alt)
                if key:
                    return alt
        return None

    def _estimate_cost(self, provider: str, model: str, tokens: int) -> float:
        """Rough cost estimate per 1K tokens."""
        rates = {
            "gemini": 0.0005, "groq": 0.0003, "openrouter": 0.001,
            "openai": 0.003, "anthropic": 0.005,
        }
        return (tokens / 1000) * rates.get(provider, 0.001)

    def _update_health(self, provider: str, success: bool, duration: float) -> None:
        h = self._health.setdefault(provider, {
            "total": 0, "success": 0, "fail": 0,
            "avg_latency_ms": 0, "last_check": 0,
        })
        h["total"] += 1
        h["success" if success else "fail"] += 1
        h["last_check"] = time.time()
        alpha = 0.1
        h["avg_latency_ms"] = h["avg_latency_ms"] * (1 - alpha) + (duration * 1000) * alpha

    async def health_check(self) -> Dict[str, Any]:
        """Full health report across all providers."""
        return {
            "providers": {
                p: {
                    **self._health.get(p, {}),
                    "circuit": self._breakers[p].state.value if p in self._breakers else "unknown",
                    "keys": self._key_mgr.get_provider_status(p),
                }
                for p in self.PROVIDER_ENDPOINTS
            },
            "cache": self._cache.stats,
            "queue": self._queue.stats,
            **self._stats,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "health": self._health}


# Singleton
_gateway: Optional[InternalAPIGateway] = None
def get_api_gateway() -> InternalAPIGateway:
    global _gateway
    if _gateway is None:
        _gateway = InternalAPIGateway()
    return _gateway


