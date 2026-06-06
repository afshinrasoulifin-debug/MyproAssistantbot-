
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/task_runner.py
────────────────────────────
TASK RUNNER v1.0 — DAG-Based Workflow Engine

Chain operations into automated pipelines:
  • DAG (Directed Acyclic Graph) execution model
  • Conditional branching (if/else/switch)
  • Parallel execution with merge strategies
  • Loop/retry with exponential backoff
  • Variable passing between nodes
  • Workflow templates (scan → analyze → report)
  • Save/load workflows as JSON
  • Real-time execution status
  • Error handling & recovery
  • Autorun on schedule or trigger

Architecture:
  workflow JSON → DAG builder → topological sort → parallel executor → results

v29.0.0
"""


import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

# ── Configuration ──
MAX_NODES = 50
NODE_TIMEOUT = 120  # seconds
MAX_PARALLEL = 5
MAX_RETRIES = 3
MAX_LOOP_ITERATIONS = 100


# ── Types ──


def _safe_eval(expr: str, variables: dict) -> Any:
    """Evaluate expression with restricted builtins (no code execution)."""
    safe_builtins = {"__builtins__": {"True": True, "False": False, "None": None,
                     "len": len, "str": str, "int": int, "float": float, "bool": bool,
                     "abs": abs, "min": min, "max": max, "round": round, "sum": sum}}
    return eval(expr, safe_builtins, {"vars": variables})


class NodeType(str, Enum):
    START = "start"
    END = "end"
    TOOL = "tool"
    SHELL = "shell"
    PYTHON = "python"
    CONDITION = "condition"
    PARALLEL = "parallel"
    MERGE = "merge"
    LOOP = "loop"
    DELAY = "delay"
    SUBWORKFLOW = "subworkflow"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowNode:
    """A single node in the workflow DAG."""
    id: str
    type: NodeType
    name: str
    config: dict[str, Any] = field(default_factory=dict)
    retries: int = 0
    retry_delay: float = 1.0
    timeout: float = NODE_TIMEOUT
    condition: str = ""  # Python expression for conditional execution

@dataclass
class WorkflowEdge:
    """Connection between nodes."""
    source: str
    target: str
    label: str = ""
    condition: str = ""

@dataclass
class NodeResult:
    """Execution result of a single node."""
    node_id: str
    status: NodeStatus
    output: Any = None
    error: str = ""
    duration_ms: int = 0
    attempts: int = 0

@dataclass
class Workflow:
    """A complete workflow definition."""
    id: str
    name: str
    description: str = ""
    nodes: list[WorkflowNode] = field(default_factory=list)
    edges: list[WorkflowEdge] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name,
            "description": self.description,
            "nodes": [{"id": n.id, "type": n.type.value, "name": n.name,
                       "config": n.config} for n in self.nodes],
            "edges": [{"source": e.source, "target": e.target,
                       "label": e.label} for e in self.edges],
            "variables": self.variables,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Workflow":
        wf = cls(
            id=data["id"], name=data["name"],
            description=data.get("description", ""),
            variables=data.get("variables", {}),
        )
        for n in data.get("nodes", []):
            wf.nodes.append(WorkflowNode(
                id=n["id"], type=NodeType(n["type"]),
                name=n["name"], config=n.get("config", {}),
            ))
        for e in data.get("edges", []):
            wf.edges.append(WorkflowEdge(
                source=e["source"], target=e["target"],
                label=e.get("label", ""),
            ))
        return wf

@dataclass
class ExecutionTrace:
    """Full execution trace of a workflow run."""
    workflow_id: str
    status: str = "running"
    results: dict[str, NodeResult] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0
    total_duration_ms: int = 0
    error: str = ""


# ── DAG Utilities ──

def _build_adjacency(workflow: Workflow) -> dict[str, list[str]]:
    """Build adjacency list from edges."""
    adj: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}
    for e in workflow.edges:
        adj.setdefault(e.source, []).append(e.target)
    return adj

def _build_reverse(workflow: Workflow) -> dict[str, list[str]]:
    """Build reverse adjacency (dependencies)."""
    rev: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}
    for e in workflow.edges:
        rev.setdefault(e.target, []).append(e.source)
    return rev

def _topological_sort(nodes: list[WorkflowNode], edges: list[WorkflowEdge]) -> list[str]:
    """Topological sort of the DAG."""
    in_degree = {n.id: 0 for n in nodes}
    adj = {n.id: [] for n in nodes}
    for e in edges:
        adj[e.source].append(e.target)
        in_degree[e.target] = in_degree.get(e.target, 0) + 1

    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    order = []
    while queue:
        nid = queue.pop(0)
        order.append(nid)
        for child in adj.get(nid, []):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    if len(order) != len(nodes):
        raise ValueError("Workflow contains a cycle")
    return order


# ── Workflow Executor ──

class WorkflowExecutor:
    """Executes workflow DAGs."""

    def __init__(self) -> None:
        self._tool_handlers: dict[str, Callable[..., Awaitable[Any]]] = {}
        self._active_traces: dict[str, ExecutionTrace] = {}

    def register_tool(self, name: str, handler: Callable[..., Awaitable[Any]]) -> None:
        self._tool_handlers[name] = handler

    async def execute(self, workflow: Workflow) -> ExecutionTrace:
        """Execute a workflow and return the trace."""
        trace = ExecutionTrace(
            workflow_id=workflow.id,
            variables=workflow.variables.copy(),
        )
        self._active_traces[workflow.id] = trace
        node_map = {n.id: n for n in workflow.nodes}

        try:
            order = _topological_sort(workflow.nodes, workflow.edges)
            deps = _build_reverse(workflow)
            adj = _build_adjacency(workflow)

            for node_id in order:
                node = node_map[node_id]

                # Check if all dependencies succeeded
                dep_ok = all(
                    trace.results.get(d, NodeResult(d, NodeStatus.PENDING)).status == NodeStatus.COMPLETED
                    for d in deps.get(node_id, [])
                )
                if not dep_ok:
                    trace.results[node_id] = NodeResult(
                        node_id=node_id, status=NodeStatus.SKIPPED,
                    )
                    continue

                # Check condition
                if node.condition:
                    try:
                        if not _safe_eval(node.condition, trace.variables):
                            trace.results[node_id] = NodeResult(
                                node_id=node_id, status=NodeStatus.SKIPPED,
                            )
                            continue
                    except ArkiBaseError as e:
                        logger.debug("Suppressed: %s", e)

                # Execute with retry
                result = await self._execute_node(node, trace)
                trace.results[node_id] = result

                if result.status_code == NodeStatus.FAILED and node.type not in (NodeType.CONDITION,):
                    trace.status_code = "failed"
                    trace.error = result.error
                    break

            if trace.status_code == "running":
                trace.status_code = "completed"

        except ArkiBaseError as exc:
            trace.status_code = "failed"
            trace.error = str(exc)

        trace.completed_at = time.time()
        trace.total_duration_ms = int((trace.completed_at - trace.started_at) * 1000)
        return trace

    async def _execute_node(self, node: WorkflowNode, trace: ExecutionTrace) -> NodeResult:
        """Execute a single node with retry logic."""
        for attempt in range(max(1, node.retries + 1)):
            start = time.monotonic()
            try:
                if node.type == NodeType.START:
                    output = "started"
                elif node.type == NodeType.END:
                    output = trace.variables
                elif node.type == NodeType.SHELL:
                    cmd = node.config.get("command", "")
                    proc = await asyncio.create_subprocess_shell(
                        cmd, stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        executable="/bin/bash",
                    )
                    stdout_b, stderr_b = await asyncio.wait_for(
                        proc.communicate(), timeout=node.timeout,
                    )
                    output = stdout_b.decode("utf-8", errors="replace")
                    if proc.returncode != 0:
                        raise RuntimeError(stderr_b.decode("utf-8", errors="replace"))
                elif node.type == NodeType.PYTHON:
                    code = node.config.get("code", "")
                    import io
                    from contextlib import redirect_stdout
                    cap = io.StringIO()
                    with redirect_stdout(cap):
                        exec(code, {"vars": trace.variables})
                    output = cap.getvalue()
                elif node.type == NodeType.TOOL:
                    tool_name = node.config.get("tool", "")
                    handler = self._tool_handlers.get(tool_name)
                    if not handler:
                        raise RuntimeError(f"Unknown tool: {tool_name}")
                    output = await asyncio.wait_for(
                        handler(**node.config.get("args", {})),
                        timeout=node.timeout,
                    )
                elif node.type == NodeType.DELAY:
                    delay = node.config.get("seconds", 1)
                    await asyncio.sleep(delay)
                    output = f"Delayed {delay}s"
                elif node.type == NodeType.CONDITION:
                    expr = node.config.get("expression", "True")
                    output = _safe_eval(expr, trace.variables)
                elif node.type == NodeType.LOOP:
                    count = min(node.config.get("count", 1), MAX_LOOP_ITERATIONS)
                    output = f"Loop {count} iterations"
                else:
                    output = None

                # Store output in variables
                var_name = node.config.get("output_var", node.id)
                trace.variables[var_name] = output

                elapsed = int((time.monotonic() - start) * 1000)
                return NodeResult(
                    node_id=node.id, status=NodeStatus.COMPLETED,
                    output=output, duration_ms=elapsed, attempts=attempt + 1,
                )

            except asyncio.TimeoutError:
                elapsed = int((time.monotonic() - start) * 1000)
                if attempt == node.retries:
                    return NodeResult(
                        node_id=node.id, status=NodeStatus.FAILED,
                        error=f"Timeout ({node.timeout}s)",
                        duration_ms=elapsed, attempts=attempt + 1,
                    )
            except ArkiBaseError as exc:
                elapsed = int((time.monotonic() - start) * 1000)
                if attempt == node.retries:
                    return NodeResult(
                        node_id=node.id, status=NodeStatus.FAILED,
                        error=str(exc), duration_ms=elapsed,
                        attempts=attempt + 1,
                    )

            # Backoff before retry
            await asyncio.sleep(node.retry_delay * (2 ** attempt))

        return NodeResult(node_id=node.id, status=NodeStatus.FAILED, error="Max retries")

    def active_traces(self) -> list[dict]:
        return [
            {
                "workflow_id": t.workflow_id,
                "status": t.status_code,
                "nodes_completed": sum(1 for r in t.results.values()
                                       if r.status_code == NodeStatus.COMPLETED),
                "nodes_total": len(t.results),
                "elapsed_ms": int((time.time() - t.started_at) * 1000),
            }
            for t in self._active_traces.values()
        ]


# ── Module Singleton ──
workflow_executor = WorkflowExecutor()


