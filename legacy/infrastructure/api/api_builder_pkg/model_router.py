
"""
api_builder_pkg/model_router.py — ModelRouter
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ModelRouter:
    """Routes requests to the optimal model from the full registry.

    Strategy:
      AUTO       → Smart selection based on task type
      FAST       → Low latency: Groq, Gemini Flash, APEX Fast tier
      PRO        → Balanced: Gemini Pro, APEX Standard/Smart/Pro
      ULTRA      → Highest quality: APEX Power/Ultra + Elite models
      CONSORTIUM → Multi-model synthesis
    """

    def __init__(self):
        self._request_count = 0
        self._model_latencies: Dict[str, List[float]] = defaultdict(list)
        self._tier_pools: Optional[Dict[ModelTier, List[str]]] = None

    def _build_tier_pools(self) -> Dict[ModelTier, List[str]]:
        """Build tier pools dynamically from models_registry."""
        if self._tier_pools is not None:
            return self._tier_pools

        pools = {
            ModelTier.FAST: [],
            ModelTier.PRO: [],
            ModelTier.ULTRA: [],
        }

        try:
            from arki_project.utils.models_registry import MODELS, APEX_TIERS

            # Base models
            for key, info in MODELS.items():
                if info.provider == "groq":
                    pools[ModelTier.FAST].append(key)
                elif info.provider == "gemini":
                    pools[ModelTier.PRO].append(key)

            # APEX tiers
            tier_mapping = {
                "fast": ModelTier.FAST,
                "standard": ModelTier.PRO,
                "smart": ModelTier.PRO,
                "pro": ModelTier.PRO,
                "power": ModelTier.ULTRA,
                "ultra": ModelTier.ULTRA,
            }
            for apex_name, apex_data in APEX_TIERS.items():
                target = tier_mapping.get(apex_name, ModelTier.PRO)
                for key in apex_data["models"]:
                    if key not in pools[target]:
                        pools[target].append(key)

            # Elite models → ULTRA
            for key in ("g-qwen37-max", "g-kimi26-think", "g-deepseek-v4-p",
                        "g-glm51-think", "g-nemotron3-sup", "g-qwen3-coder"):
                if key not in pools[ModelTier.ULTRA]:
                    pools[ModelTier.ULTRA].append(key)

        except ImportError:
            # Fallback
            pools[ModelTier.FAST] = ["gemini-flash", "llama8"]
            pools[ModelTier.PRO] = ["gemini-pro", "llama70"]
            pools[ModelTier.ULTRA] = ["gemini-pro"]

        self._tier_pools = pools
        return pools

    def select_model(self, tier: ModelTier, specific_model: Optional[str] = None,
                     task_type: str = "general") -> str:
        """Select optimal model for the request."""
        self._request_count += 1

        if specific_model:
            return specific_model

        if tier == ModelTier.AUTO:
            return self._auto_select(task_type)
        elif tier == ModelTier.CONSORTIUM:
            return "__consortium__"

        pools = self._build_tier_pools()
        pool = pools.get(tier, pools[ModelTier.PRO])
        if not pool:
            return "gemini-pro"

        # Pick model with best average latency (adaptive)
        if self._model_latencies:
            scored = []
            for m in pool:
                lats = self._model_latencies.get(m, [])
                avg = sum(lats[-10:]) / len(lats[-10:]) if lats else 9999
                scored.append((m, avg))
            scored.sort(key=lambda x: x[1])
            return scored[0][0]
        return pool[0]

    def _auto_select(self, task_type: str) -> str:
        """Smart model selection based on task type."""
        # Coding tasks → Qwen3 Coder (Elite 480B)
        if task_type in ("code", "debug", "refactor", "review"):
            return "g-qwen3-coder"
        # Analysis/research → Gemini Pro or DeepSeek V4
        elif task_type in ("analysis", "research", "complex"):
            return "g-deepseek-v4-p"
        # Creative writing → GPT-5 or Qwen 3.7 Max
        elif task_type in ("creative", "writing", "story"):
            return "g-qwen37-max"
        # Fast/simple → Gemini Flash
        elif task_type in ("fast", "simple", "translate"):
            return "gemini-flash"
        # Math/reasoning → DeepSeek R1
        elif task_type in ("math", "reasoning", "logic"):
            return "g-deepseek-r1"
        # Agent tasks → Kimi K2.6
        elif task_type in ("agent", "planning", "orchestration"):
            return "g-kimi26-think"
        # Persian → GLM 5.1 (strong multilingual)
        elif task_type in ("persian", "farsi", "multilingual"):
            return "g-glm51-think"
        # Default → Gemini Pro
        return "gemini-pro"

    def record_latency(self, model: str, latency_ms: float):
        self._model_latencies[model].append(latency_ms)
        if len(self._model_latencies[model]) > 100:
            self._model_latencies[model] = self._model_latencies[model][-50:]

    def get_model_stats(self) -> Dict[str, Dict]:
        stats = {}
        for model, lats in self._model_latencies.items():
            recent = lats[-20:]
            stats[model] = {
                "total_calls": len(lats),
                "avg_latency_ms": sum(recent) / len(recent) if recent else 0,
                "min_latency_ms": min(recent) if recent else 0,
                "max_latency_ms": max(recent) if recent else 0,
            }
        return stats

    def get_all_models_count(self) -> int:
        """Get total model count from registry."""
        try:
            from arki_project.utils.models_registry import MODELS
            return len(MODELS)
        except ImportError:
            return 0





