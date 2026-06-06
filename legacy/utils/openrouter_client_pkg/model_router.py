
"""
openrouter_client_pkg/model_router.py — ModelRouter
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ModelRouter:
    """
    Intelligent model routing based on task, cost, and quality.

    Selects the optimal model for each request.
    """

    # Task → model preference mapping
    TASK_PREFERENCES: Dict[TaskType, List[str]] = {
        TaskType.CHAT: ["free", "fast"],
        TaskType.CODE: ["code", "reasoning"],
        TaskType.ANALYSIS: ["reasoning", "large"],
        TaskType.CREATIVE: ["large", "multilingual"],
        TaskType.SUMMARIZE: ["fast", "free"],
        TaskType.TRANSLATE: ["multilingual", "free"],
        TaskType.REASONING: ["reasoning", "chain-of-thought"],
        TaskType.FUNCTION: ["function"],
    }

    def __init__(self, circuit_breaker: CircuitBreaker) -> None:
        self.circuit_breaker = circuit_breaker

    def select(
        self,
        task: TaskType = TaskType.CHAT,
        max_tier: ModelTier = ModelTier.FREE,
        require_functions: bool = False,
        require_vision: bool = False,
        min_context: int = 4096,
        preferred_provider: Optional[str] = None,
    ) -> Optional[ModelInfo]:
        """Select the best model for a task."""
        tier_order = [
            ModelTier.FREE, ModelTier.BUDGET,
            ModelTier.STANDARD, ModelTier.PREMIUM,
        ]
        max_tier_idx = tier_order.index(max_tier)

        candidates = []
        for model_id, model in MODEL_REGISTRY.items():
            # Filter by constraints
            if tier_order.index(model.tier) > max_tier_idx:
                continue
            if require_functions and not model.supports_functions:
                continue
            if require_vision and not model.supports_vision:
                continue
            if model.context_length < min_context:
                continue
            if not self.circuit_breaker.can_use(model_id):
                continue
            if preferred_provider and model.provider.lower() != preferred_provider.lower():
                continue

            candidates.append(model)

        if not candidates:
            return None

        # Score candidates based on task preferences
        preferred_tags = self.TASK_PREFERENCES.get(task, [])
        scored = []
        for model in candidates:
            score = model.quality_rating
            for tag in preferred_tags:
                if tag in model.tags:
                    score += 0.2

            # Prefer free models
            if model.tier == ModelTier.FREE:
                score += 0.1

            scored.append((score, model))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def get_fallback_chain(self, primary: str,
                           max_fallbacks: int = 3) -> List[str]:
        """Build a fallback chain of models."""
        chain = [primary]
        primary_info = MODEL_REGISTRY.get(primary)
        if not primary_info:
            return chain

        # Find similar models as fallbacks
        for model_id, model in MODEL_REGISTRY.items():
            if model_id == primary:
                continue
            if not self.circuit_breaker.can_use(model_id):
                continue
            if len(chain) >= max_fallbacks + 1:
                break
            chain.append(model_id)

        return chain


# ═══════════════════════════════════════════════════════════════════
# Request Cache
# ═══════════════════════════════════════════════════════════════════



