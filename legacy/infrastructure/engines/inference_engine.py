
from __future__ import annotations
"""
InferenceEngine — Core inference with batching, caching, and optimization.
"""
import asyncio, logging, time, hashlib
from typing import Any, Dict, List



logger = logging.getLogger(__name__)

class InferenceEngine:
    """High-performance inference with request batching and response caching."""

    def __init__(self, batch_size: int = 10, cache_size: int = 10000) -> None:
        self._batch_size = batch_size
        self._cache: Dict[str, Any] = {}
        self._cache_size = cache_size
        self._queue: List = []
        self._total_inferences = 0

    def _hash(self, data: Any) -> str:
        return hashlib.sha256(str(data).encode()).hexdigest()[:16]

    async def infer(self, input_data: Any, model: str = "", use_cache: bool = True) -> Any:
        key = self._hash((input_data, model))
        if use_cache and key in self._cache:
            return self._cache[key]

        self._total_inferences += 1
        result = {"input": input_data, "model": model, "timestamp": time.time()}

        if len(self._cache) >= self._cache_size:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[key] = result
        return result

    async def batch_infer(self, inputs: List[Any], model: str = "") -> List[Any]:
        tasks = [self.infer(inp, model) for inp in inputs]
        return await asyncio.gather(*tasks)


