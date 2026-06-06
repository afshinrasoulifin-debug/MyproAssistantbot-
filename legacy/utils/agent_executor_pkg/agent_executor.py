
"""
agent_executor_pkg/agent_executor.py — AgentExecutor
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class AgentExecutor:
    """
    Class-based wrapper around the functional agent execution engine.
    Provides an OOP interface compatible with module_bridge and external callers.
    """

    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self._scheduler = StepScheduler()
        self._history = TraceHistory()
        # Ensure tools registered
        if len(registry.get_all()) == 0:
            register_builtin_tools()

    async def execute(self, query: str, messages: List[Dict[str, str]] = None) -> ExecutionTrace:
        """Execute the agent with the given query."""
        return await execute_agent(query, messages or [], self.config)

    def get_tools(self) -> List[Tool]:
        """Get all registered tools."""
        return registry.get_all()

    def get_tool_names(self) -> List[str]:
        """Get all registered tool names."""
        return [t.name for t in registry.get_all()]

    def get_tool_count(self) -> int:
        """Get number of registered tools."""
        return len(registry.get_all())

    def get_categories(self) -> List[str]:
        """Get all tool categories."""
        return list(set(t.category.value for t in registry.get_all() if t.category))

    @property
    def tool_registry(self) -> ToolRegistry:
        """Access the tool registry."""
        return registry

    @property
    def history(self) -> TraceHistory:
        """Access execution history."""
        return self._history

    def status(self) -> dict:
        """Get agent executor status."""
        tools = registry.get_all()
        categories = {}
        for t in tools:
            cat = t.category.value if t.category else "uncategorized"
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "version": "2.0.0-TITANIUM",
            "tools": len(tools),
            "categories": categories,
            "config": {
                "model": self.config.model,
                "max_steps": self.config.max_steps,
                "parallel": self.config.parallel_tools,
            },
        }


# Singleton instances


