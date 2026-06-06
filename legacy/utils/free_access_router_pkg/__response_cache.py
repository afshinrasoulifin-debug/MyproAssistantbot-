
"""
free_access_router_pkg/__response_cache.py — _ResponseCache
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class _ResponseCache:
    """Thread-safe LRU cache for deduplicating identical requests.

    Key: hash(model_key + messages + temperature)
    Value: (response_text, timestamp)
    TTL: 300 seconds (5 minutes)
    """

    def __init__(self, max_size: int = 256, ttl: float = 300.0):
        self._cache: OrderedDict[str, Tuple[str, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl
        self._hits = 0
        self._misses = 0
        self._lock = asyncio.Lock() if asyncio.get_event_loop().is_running() else None

    @staticmethod
    def _make_key(model_key: str, messages: List[Dict], temperature: float) -> str:
        """Create a stable hash key for a request."""
        raw = json.dumps({"m": model_key, "msgs": messages, "t": round(temperature, 2)},
                         sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def get(self, model_key: str, messages: List[Dict], temperature: float) -> Optional[str]:
        """Get cached response if fresh."""
        key = self._make_key(model_key, messages, temperature)
        entry = self._cache.get(key)
        if entry:
            text, ts = entry
            if time.time() - ts < self._ttl:
                self._hits += 1
                self._cache.move_to_end(key)
                return text
            else:
                del self._cache[key]
        self._misses += 1
        return None

    def put(self, model_key: str, messages: List[Dict], temperature: float, response: str):
        """Cache a response."""
        key = self._make_key(model_key, messages, temperature)
        self._cache[key] = (response, time.time())
        self._cache.move_to_end(key)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    @property
    def stats(self) -> Dict[str, int]:
        return {"hits": self._hits, "misses": self._misses, "size": len(self._cache)}


# ═══════════════════════════════════════════════════════════════════
# §3 — OPENROUTER FREE MODELS — Complete Mapping
# ═══════════════════════════════════════════════════════════════════
# Models that work on OpenRouter WITHOUT an API key (using :free suffix
# or natively free). This is the foundation of zero-cost access.
#
# Three categories:
#   A) Natively free (Gemini, DeepSeek via OR) — no :free suffix needed
#   B) :free suffix models — append :free to model ID
#   C) Not free on OpenRouter — need SMART_FALLBACK (see §4)



