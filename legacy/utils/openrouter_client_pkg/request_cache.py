
"""
openrouter_client_pkg/request_cache.py — RequestCache
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class RequestCache:
    """Cache for LLM responses."""

    def __init__(self, max_size: int = 500,
                 ttl: float = 3600) -> None:
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.hits = 0
        self.misses = 0

    def _key(self, model: str, messages: List[Dict],
             params: Dict) -> str:
        raw = json.dumps({
            "model": model,
            "messages": messages,
            "params": params,
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, model: str, messages: List[Dict],
            params: Dict) -> Optional[ChatResponse]:
        key = self._key(model, messages, params)
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] <= self.ttl:
                self.hits += 1
                return entry["response"]
            del self.cache[key]
        self.misses += 1
        return None

    def put(self, model: str, messages: List[Dict],
            params: Dict, response: ChatResponse) -> None:
        key = self._key(model, messages, params)
        if len(self.cache) >= self.max_size:
            oldest = min(self.cache, key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest]
        self.cache[key] = {
            "response": response,
            "timestamp": time.time(),
        }


# ═══════════════════════════════════════════════════════════════════
# Context Manager
# ═══════════════════════════════════════════════════════════════════



