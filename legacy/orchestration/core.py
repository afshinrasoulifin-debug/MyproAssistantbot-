
from __future__ import annotations
"""
arki_project/orchestration/core.py — Orchestrator v10 (Optimized)
═══════════════════════════════════════════════════════════
Wires all components into a single entry point for AI inference.

Author: Manus AI
"""


import asyncio
import logging
import time
import uuid
import os
from typing import Any, Dict, List, Optional, Final

from .types import (
    InferenceRequest,
    InferenceResponse,
    ProviderName,
    RequestPriority,
)

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE: Final[bool] = True
except ImportError:
    _TITANIUM_ACTIVE: Final[bool] = False

from .provider_router import (
    ProviderCapability,
    ProviderRouter,
)
from .load_balancer import LoadBalancer, Strategy
from .retry_manager import RetryManager, RetryConfig
from .cache_layer import CacheLayer
from .work_queue import WorkQueue
from .observatory import Observatory

# Configure logging
logger = logging.getLogger("arki.orchestration.core")


class RateLimitError(Exception):
    """Exception raised when a provider returns a 429 status code."""

class OverloadedError(Exception):
    """Exception raised when a provider returns a 503 status code."""

class ProviderError(Exception):
    """Generic exception for provider-side failures."""


class Orchestrator:
    """
    The central brain of the AI infrastructure.
    
    Coordinates routing, load balancing, caching, and retries across 
    multiple AI providers. Integrates with the Surgeon Agent for 
    autonomous self-healing.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initializes the Orchestrator with the given configuration.
        
        Args:
            config (Dict[str, Any]): Configuration parameters for all sub-components.
        """
        self._config: Dict[str, Any] = config
        self._booted: bool = False

        # Core Components
        self.router: ProviderRouter = ProviderRouter()
        self.balancer: LoadBalancer = LoadBalancer(
            strategy=Strategy(config.get("lb_strategy", "latency_aware")),
        )
        self.retry: RetryManager = RetryManager(
            config=RetryConfig(
                max_retries=config.get("max_retries", 5),
                base_delay=config.get("retry_base_delay", 1.0),
                max_delay=config.get("retry_max_delay", 30.0),
            ),
        )
        self.cache: CacheLayer = CacheLayer(
            inference_max=config.get("cache_inference_max", 10_000),
            inference_ttl=config.get("cache_inference_ttl", 3600.0),
        )
        self.queue: WorkQueue = WorkQueue(
            max_workers=config.get("queue_workers", 10),
            max_queue_size=config.get("queue_max_size", 1000),
            max_rps=config.get("max_rps", 50.0),
        )
        self.observatory: Observatory = Observatory()
        self.surgeon: Optional[Any] = None

        # Provider State
        self._api_keys: Dict[ProviderName, str] = {}
        self._base_urls: Dict[ProviderName, str] = {}
        self._event_bus: Optional[Any] = None
        self._last_health_update: float = 0.0
        self._health_update_interval: float = 10.0

    async def boot(self) -> None:
        """
        Initializes and starts all sub-components.
        
        Must be called exactly once before generating any responses.
        """
        if self._booted:
            return

        # Load API keys from config or environment
        self._api_keys = {
            ProviderName.GEMINI: self._config.get("gemini_api_key") or os.environ.get("AI_API_KEY", ""),
            ProviderName.GROQ: self._config.get("groq_api_key") or os.environ.get("GROQ_API_KEY", ""),
            ProviderName.OPENROUTER: self._config.get("openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY", ""),
        }

        self._base_urls = {
            ProviderName.GEMINI: "https://generativelanguage.googleapis.com/v1beta",
            ProviderName.GROQ: "https://api.groq.com/openai/v1",
            ProviderName.OPENROUTER: "https://openrouter.ai/api/v1",
        }

        # Component Initialization
        self._register_providers()
        self._setup_circuit_breakers()
        self._connect_event_bus()
        
        self.queue.set_handler(self._process_queue_job)
        await self.queue.start()

        # Integrate Surgeon Agent
        try:
            from arki_project.orchestration.surgeon import surgeon
            self.surgeon = surgeon
            asyncio.create_task(self.surgeon.start())
        except Exception as e:
            logger.warning(f"Surgeon Agent integration failed: {e}")

        self._booted = True
        logger.info(f"🎼 Orchestrator booted — {sum(1 for k in self._api_keys.values() if k)} providers ready")

    def _setup_circuit_breakers(self) -> None:
        """Configures circuit breakers for each provider."""
        self.retry.register_breaker(ProviderName.GEMINI, failure_threshold=5, recovery_timeout=60)
        self.retry.register_breaker(ProviderName.GROQ, failure_threshold=5, recovery_timeout=60)
        self.retry.register_breaker(ProviderName.OPENROUTER, failure_threshold=3, recovery_timeout=120)

    def _register_providers(self) -> None:
        """Registers provider capabilities based on the models registry."""
        try:
            from arki_project.utils.models_registry import MODELS
        except ImportError:
            logger.warning("Models registry not found; no providers registered.")
            return

        # Simplified registration logic for enterprise standards
        for provider_name in [ProviderName.GEMINI, ProviderName.GROQ, ProviderName.OPENROUTER]:
            if not self._api_keys.get(provider_name):
                continue
                
            models = {k: v.id for k, v in MODELS.items() if v.provider == provider_name.value.lower()}
            if provider_name == ProviderName.OPENROUTER:
                # OpenRouter serves as a universal fallback
                models.update({k: v.id for k, v in MODELS.items()})
                
            cap = ProviderCapability(
                name=provider_name,
                models=models,
                priority=10 if provider_name == ProviderName.GEMINI else (8 if provider_name == ProviderName.GROQ else 3)
            )
            self.router.register_provider(cap)
            for model_id in models.values():
                self.balancer.add_endpoint(provider_name, model_id, weight=1.0 if cap.priority > 5 else 0.5)

    def _connect_event_bus(self) -> None:
        """Connects to the infrastructure event bus if available."""
        try:
            from arki_project.infrastructure.boot import get_infra
            infra = get_infra()
            if infra and "event_bus" in infra:
                self._event_bus = infra["event_bus"]
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)

    async def _process_queue_job(self, job: Any) -> None:
        """Handler for processing background jobs from the work queue."""
        # Implementation details for queue processing
        pass

    async def generate(
        self,
        prompt: str,
        *,
        messages: Optional[List[Dict[str, str]]] = None,
        model_key: str = "",
        user_id: int = 0,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        use_cache: bool = True,
        priority: RequestPriority = RequestPriority.NORMAL,
        thinking_agent: Optional[Any] = None,
        **kwargs: Any
    ) -> InferenceResponse:
        """
        Generates an AI response through the full orchestration pipeline.
        """
        request_id: str = uuid.uuid4().hex[:12]
        last_msg: str = messages[-1]["content"] if messages else prompt

        if thinking_agent:
            await thinking_agent.add_reasoning_step("ORCHESTRATION", f"شروع فرآیند ارکستراسیون برای درخواست {request_id}")

        # 1. Cache Check
        if use_cache:
            if thinking_agent: await thinking_agent.update_thought("بررسی حافظه کش...", status_emoji="💾")
            cached_text = self.cache.get_inference(last_msg, model_key, temperature)
            if cached_text:
                if thinking_agent: await thinking_agent.add_reasoning_step("CACHE_HIT", "پاسخ از حافظه کش بازیابی شد.")
                return InferenceResponse(
                    text=cached_text,
                    provider=ProviderName.GEMINI,
                    model_id=model_key,
                    cached=True
                )

        # 2. Routing & Load Balancing
        if thinking_agent: await thinking_agent.update_thought("مسیریابی هوشمند بین مدل‌ها...", status_emoji="🛤️")
        request = InferenceRequest(
            prompt=prompt,
            messages=messages,
            model_key=model_key,
            user_id=user_id,
            temperature=temperature,
            max_tokens=max_tokens,
            priority=priority
        )
        decision = self.router.route(request)
        
        if not decision.providers:
            raise ProviderError("هیچ پرووایدر فعالی برای این درخواست یافت نشد.")

        # 3. Execution with Resilience
        if thinking_agent: 
            await thinking_agent.add_reasoning_step("ROUTING", f"انتخاب مدل: {decision.model_id} از {decision.providers[0]}")
            await thinking_agent.update_thought(f"در حال تولید پاسخ با {decision.model_id}...", status_emoji="🧠")

        # Integration with AIClient for actual execution
        from arki_project.utils.ai_client import get_ai_client
        ai_client = get_ai_client()
        
        start_time = time.time()
        try:
            # We use the thinking_agent's resilience engine if available
            if thinking_agent:
                response_text = await thinking_agent.execute_with_resilience(
                    func=ai_client.ask,
                    step_index=thinking_agent.current_step_index if hasattr(thinking_agent, 'current_step_index') else 0,
                    primary_model_key=model_key or decision.model_id,
                    user_id=user_id,
                    prompt=prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            else:
                response_text = await ai_client.ask(
                    prompt=prompt,
                    messages=messages,
                    model_key=model_key or decision.model_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            
            latency = (time.time() - start_time) * 1000
            
            if thinking_agent:
                await thinking_agent.add_reasoning_step("EXECUTION", f"پاسخ با موفقیت در {latency:.0f}ms دریافت شد.")

            return InferenceResponse(
                text=response_text,
                provider=decision.providers[0],
                model_id=decision.model_id,
                latency_ms=latency
            )
            
        except Exception as e:
            if thinking_agent:
                await thinking_agent.recursive_review(f"خطای بحرانی در اجرا: {str(e)}")
            if self.surgeon:
                await self.surgeon.bypass_and_regenerate(decision.providers[0].value)
            raise ProviderError(f"خطا در تولید پاسخ: {str(e)}")

# Global singleton getter
_orchestrator: Optional[Orchestrator] = None

def get_orchestrator(config: Optional[Dict[str, Any]] = None) -> Orchestrator:
    """Returns the global Orchestrator instance, initializing it if necessary."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator(config or {})
    return _orchestrator


