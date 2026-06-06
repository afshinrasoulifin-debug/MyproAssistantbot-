
"""
multi_llm_orchestrator_pkg/response_cache.py — ResponseCache
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ResponseCache:
    """Cache for model responses keyed by (model + query) hash."""

    def __init__(self, max_size: int = CACHE_MAX_SIZE, ttl: float = CACHE_TTL_S):
        self._cache: OrderedDict[str, Tuple[OrchestrationResult, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _key(query: str, mode: str) -> str:
        raw = json.dumps({"q": query, "m": mode}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, query: str, mode: str) -> Optional[OrchestrationResult]:
        k = self._key(query, mode)
        if k in self._cache:
            result, ts = self._cache[k]
            if time.time() - ts < self._ttl:
                self._cache.move_to_end(k)
                self._hits += 1
                result.cache_hit = True
                return result
            del self._cache[k]
        self._misses += 1
        return None

    def put(self, query: str, mode: str, result: OrchestrationResult) -> None:
        k = self._key(query, mode)
        self._cache[k] = (result, time.time())
        self._cache.move_to_end(k)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    @property
    def hit_rate(self) -> str:
        total = self._hits + self._misses
        return f"{self._hits / total * 100:.1f}%" if total > 0 else "N/A"




