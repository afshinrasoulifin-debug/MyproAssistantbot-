
from __future__ import annotations
"""SmartGateway — AI-powered request routing with learning."""
import logging, time
from collections import defaultdict
from typing import Dict
from arki_project.infrastructure.gateway.ai_gateway import AIGateway, GatewayRequest, GatewayResponse



logger = logging.getLogger(__name__)

class SmartGateway(AIGateway):
    """Gateway that learns optimal routing from past requests."""

    def __init__(self) -> None:
        super().__init__()
        self._performance_log: Dict[str, list] = defaultdict(list)

    async def process(self, request: GatewayRequest) -> GatewayResponse:
        resp = await super().process(request)
        self._performance_log[request.model].append({
            "latency": resp.latency, "success": resp.success,
            "tokens": resp.tokens_used, "time": time.time()
        })
        return resp

    def recommend_model(self, task_type: str = "standard") -> str:
        best_model, best_score = "", 0.0
        for model, logs in self._performance_log.items():
            recent = logs[-50:]
            if not recent:
                continue
            success_rate = sum(1 for l in recent if l["success"]) / len(recent)
            avg_latency = sum(l["latency"] for l in recent) / len(recent)
            score = success_rate / max(avg_latency, 0.1)
            if score > best_score:
                best_score = score
                best_model = model
        return best_model or "gemini-pro"


