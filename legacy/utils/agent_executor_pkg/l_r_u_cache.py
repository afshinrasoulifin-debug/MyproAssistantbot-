
"""
agent_executor_pkg/l_r_u_cache.py — LRUCache
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class LRUCache:
    """Least-recently-used cache with time-to-live expiry."""

    def __init__(self, max_size: int = TOOL_CACHE_MAX_SIZE, ttl: float = TOOL_CACHE_TTL):
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(tool: str, args: dict) -> str:
        raw = json.dumps({"tool": tool, "args": args}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def get(self, tool: str, args: dict) -> Optional[ToolResult]:
        key = self._make_key(tool, args)
        if key in self._cache:
            value, ts = self._cache[key]
            if time.time() - ts < self._ttl:
                self._cache.move_to_end(key)
                self._hits += 1
                result = ToolResult(**value) if isinstance(value, dict) else value
                result.cached = True
                return result
            else:
                del self._cache[key]
        self._misses += 1
        return None

    def put(self, tool: str, args: dict, result: ToolResult) -> None:
        key = self._make_key(tool, args)
        self._cache[key] = (
            {"success": result.success, "data": result.data,
             "error": result.error, "duration_ms": result.duration_ms,
             "metadata": result.metadata},
            time.time(),
        )
        self._cache.move_to_end(key)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def invalidate(self, tool: Optional[str] = None) -> int:
        """Invalidate cache entries. If tool given, only that tool."""
        if tool is None:
            count = len(self._cache)
            self._cache.clear()
            return count
        to_remove = [k for k, (v, _) in self._cache.items()
                     if isinstance(v, dict) and v.get("_tool") == tool]
        for k in to_remove:
            del self._cache[k]
        return len(to_remove)

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self._hits / total * 100:.1f}%" if total > 0 else "N/A",
        }


# ═══════════════════════════════════════════════════════════════════
# Tool Registry
# ═══════════════════════════════════════════════════════════════════



