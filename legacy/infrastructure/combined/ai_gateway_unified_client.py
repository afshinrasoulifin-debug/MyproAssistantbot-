
from __future__ import annotations
"""
AIGatewayUnifiedClient — Combines AI Gateway + Unified Client.
Single entry point that handles gateway logic AND client abstraction.
"""
import logging, time
from typing import Any, Dict



logger = logging.getLogger(__name__)

class AIGatewayUnifiedClient:
    """Gateway that also acts as a unified client — full request lifecycle."""

    def __init__(self) -> None:
        self._providers: Dict[str, Any] = {}
        self._middleware: list = []
        self._metrics = {"requests": 0, "errors": 0, "total_latency": 0.0}

    def register_provider(self, name: str, client: Any) -> None:
        self._providers[name] = client

    def use(self, middleware: Any) -> Any:
        self._middleware.append(middleware)

    async def complete(self, messages: list, model: str = "", **kwargs) -> dict:
        self._metrics["requests"] += 1
        t0 = time.time()

        # Run middleware
        context = {"messages": messages, "model": model, **kwargs}
        for mw in self._middleware:
            context = mw(context) if not callable(getattr(mw, '__call__', None)) else mw(context)

        # Route to provider
        provider_name = self._resolve(model)
        client = self._providers.get(provider_name)
        if not client:
            self._metrics["errors"] += 1
            return {"error": f"No provider for {model}", "success": False}

        try:
            result = await client.complete(messages, model=model, **kwargs) if hasattr(client, 'complete') else {}
            self._metrics["total_latency"] += time.time() - t0
            return result
        except Exception as e:
            self._metrics["errors"] += 1
            return {"error": str(e), "success": False}

    def _resolve(self, model: str) -> str:
        if "gemini" in model: return "gemini"
        if "llama" in model or "groq" in model: return "groq"
        if "/" in model: return "openrouter"
        return list(self._providers.keys())[0] if self._providers else ""


