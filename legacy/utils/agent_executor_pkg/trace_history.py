
"""
agent_executor_pkg/trace_history.py — TraceHistory
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class TraceHistory:
    """Stores execution traces for analysis and debugging."""

    def __init__(self, max_traces: int = MAX_TRACES_HISTORY):
        self._traces: List[ExecutionTrace] = []
        self._max = max_traces

    def add(self, trace: ExecutionTrace) -> None:
        self._traces.append(trace)
        if len(self._traces) > self._max:
            self._traces = self._traces[-self._max:]

    def get_recent(self, n: int = 10) -> List[ExecutionTrace]:
        return self._traces[-n:]

    def get_by_id(self, trace_id: str) -> Optional[ExecutionTrace]:
        for t in self._traces:
            if t.id == trace_id:
                return t
        return None

    def get_stats(self) -> dict:
        if not self._traces:
            return {"total": 0}

        successful = [t for t in self._traces if t.success]
        return {
            "total": len(self._traces),
            "success_rate": f"{len(successful)/len(self._traces)*100:.1f}%",
            "avg_duration_ms": sum(t.total_duration_ms for t in self._traces) / len(self._traces),
            "avg_steps": sum(len(t.steps) for t in self._traces) / len(self._traces),
            "avg_tools": sum(t.tool_calls for t in self._traces) / len(self._traces),
            "total_cost": sum(t.total_cost for t in self._traces),
            "total_tokens": sum(t.tokens_used for t in self._traces),
        }

    def export(self) -> List[dict]:
        """Export traces as serializable dicts."""
        results = []
        for t in self._traces:
            results.append({
                "id": t.id,
                "query": t.query,
                "model": t.model,
                "success": t.success,
                "final_answer": t.final_answer[:500],
                "steps": len(t.steps),
                "tool_calls": t.tool_calls,
                "duration_ms": t.total_duration_ms,
                "cost": t.total_cost,
                "tokens": t.tokens_used,
                "status": t.status.value,
            })
        return results


# ═══════════════════════════════════════════════════════════════════
# AgentExecutor — Convenience class wrapper
# ═══════════════════════════════════════════════════════════════════



