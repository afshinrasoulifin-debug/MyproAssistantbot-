
"""
agent_executor_pkg/tool_registry.py — ToolRegistry
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._call_counts: Dict[str, int] = defaultdict(int)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._total_duration: Dict[str, float] = defaultdict(float)

    def register(self, tool: Tool) -> None:
        """Register a tool. Overwrites if name exists."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name} [{tool.category.value}]")

    def unregister(self, name: str) -> bool:
        return self._tools.pop(name, None) is not None

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def get_all(self) -> List[Tool]:
        return list(self._tools.values())

    def get_by_category(self, category: ToolCategory) -> List[Tool]:
        return [t for t in self._tools.values() if t.category == category]

    def get_by_tags(self, tags: List[str]) -> List[Tool]:
        tag_set = set(tags)
        return [t for t in self._tools.values() if tag_set & set(t.tags)]

    def get_definitions(self, filter_names: Optional[List[str]] = None) -> List[dict]:
        """Get OpenAI-compatible tool definitions."""
        tools = self.get_all()
        if filter_names:
            name_set = set(filter_names)
            tools = [t for t in tools if t.name in name_set]
        return [t.to_openai_tool() for t in tools]

    def record_call(self, name: str, duration_ms: float, error: bool = False) -> None:
        self._call_counts[name] += 1
        self._total_duration[name] += duration_ms
        if error:
            self._error_counts[name] += 1

    def get_stats(self) -> Dict[str, Any]:
        stats = {}
        for name in self._tools:
            calls = self._call_counts.get(name, 0)
            errors = self._error_counts.get(name, 0)
            total_ms = self._total_duration.get(name, 0)
            stats[name] = {
                "calls": calls,
                "errors": errors,
                "error_rate": f"{errors/calls*100:.1f}%" if calls > 0 else "0%",
                "avg_latency_ms": f"{total_ms/calls:.0f}" if calls > 0 else "N/A",
            }
        return stats


# Global registry instance


