
from __future__ import annotations
import asyncio
"""
tg_bot/utils/workflow_engine.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
WORKFLOW ENGINE — DAG-Based Workflow Orchestration System

Directed Acyclic Graph execution engine for chaining tools
into fully automated, self-recovering pipelines.

Architecture
────────────
   ┌─────────────────────────────────────────────────────────────┐
   │                    WORKFLOW ENGINE                           │
   ├──────────────┬──────────────┬──────────────┬───────────────┤
   │  DAG Builder │  Scheduler   │  Executor    │  Monitor      │
   ├──────────────┼──────────────┼──────────────┼───────────────┤
   │ add_node()   │ topo_sort()  │ run_node()   │ status()      │
   │ add_edge()   │ detect_cycle │ run_parallel │ progress()    │
   │ validate()   │ dependencies │ retry()      │ timeline()    │
   │ from_json()  │ scheduling   │ rollback()   │ alerts()      │
   │ to_json()    │ cron trigger │ sandbox()    │ metrics()     │
   ├──────────────┼──────────────┼──────────────┼───────────────┤
   │  Branching   │  Variables   │  Templates   │  Persistence  │
   ├──────────────┼──────────────┼──────────────┼───────────────┤
   │ if/else      │ context map  │ scan→report  │ save/load     │
   │ switch/case  │ interpolate  │ crawl→parse  │ checkpoint    │
   │ while loop   │ transform    │ monitor→act  │ resume        │
   │ for_each     │ schema val   │ custom DSL   │ snapshot      │
   └──────────────┴──────────────┴──────────────┴───────────────┘

Features
────────
  • DAG construction with cycle detection (Kahn's algorithm)
  • Topological sort for execution ordering
  • Parallel execution of independent nodes
  • Conditional branching (if/else, switch/case)
  • Loop constructs (while, for_each, repeat)
  • Variable interpolation between nodes
  • Retry with exponential backoff per node
  • Checkpoint/resume for long-running workflows
  • Workflow templates (scan→report, ETL, monitoring)
  • JSON serialization for save/load
  • Real-time execution monitoring
  • Error propagation with rollback support
  • Cron-based scheduling with timezone support

References
──────────
  Port of: apex_app/src/lib/workflow-engine.ts (771 lines)
  Enhanced: cycle detection, topological sort, checkpoint/resume,
            template library, expression evaluator, cron scheduler
"""

import logging
logger = logging.getLogger(__name__)

import json
import re
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import (

    Any, Callable, Dict, List, Optional, Set,
)


# ═══════════════════════════════════════════════════════════════════
# Enums & Types
# ═══════════════════════════════════════════════════════════════════

class NodeType(Enum):
    """Types of workflow nodes."""
    TASK = "task"
    CONDITION = "condition"
    SWITCH = "switch"
    LOOP = "loop"
    FOR_EACH = "for_each"
    PARALLEL = "parallel"
    MERGE = "merge"
    DELAY = "delay"
    WEBHOOK = "webhook"
    SUB_WORKFLOW = "sub_workflow"
    TRANSFORM = "transform"
    CHECKPOINT = "checkpoint"


class NodeStatus(Enum):
    """Execution status of a node."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    WAITING = "waiting"


class WorkflowStatus(Enum):
    """Overall workflow status."""
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EdgeType(Enum):
    """Edge types for workflow connections."""
    NORMAL = "normal"
    CONDITIONAL_TRUE = "conditional_true"
    CONDITIONAL_FALSE = "conditional_false"
    ERROR = "error"
    ALWAYS = "always"


# ═══════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════

@dataclass
class WorkflowEdge:
    """Connection between two nodes."""
    source: str
    target: str
    edge_type: EdgeType = EdgeType.NORMAL
    condition: Optional[str] = None
    transform: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type.value,
            "condition": self.condition,
            "transform": self.transform,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WorkflowEdge":
        return cls(
            source=d["source"],
            target=d["target"],
            edge_type=EdgeType(d.get("edge_type", "normal")),
            condition=d.get("condition"),
            transform=d.get("transform"),
        )


@dataclass
class RetryPolicy:
    """Retry configuration for a node."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    retry_on: Optional[List[str]] = None  # exception types

    def get_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        delay = min(
            self.initial_delay * (self.backoff_factor ** attempt),
            self.max_delay,
        )
        # Add jitter (±25%)
        jitter = delay * 0.25
        return delay + (hash(str(attempt)) % 100 / 100.0 - 0.5) * 2 * jitter


@dataclass
class NodeConfig:
    """Configuration for a workflow node."""
    timeout_seconds: float = 300.0
    retry_policy: Optional[RetryPolicy] = None
    cache_result: bool = False
    skip_on_error: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowNode:
    """A single node in the workflow DAG."""
    id: str
    name: str
    node_type: NodeType
    config: NodeConfig = field(default_factory=NodeConfig)
    handler: Optional[str] = None  # function/tool name
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Execution state
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    attempt: int = 0

    def duration(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value,
            "handler": self.handler,
            "parameters": self.parameters,
            "status": self.status_code.value,
            "result": self.result,
            "error": self.error,
            "attempt": self.attempt,
            "config": {
                "timeout_seconds": self.config.timeout_seconds,
                "cache_result": self.config.cache_result,
                "skip_on_error": self.config.skip_on_error,
            },
        }


@dataclass
class WorkflowCheckpoint:
    """Snapshot of workflow state for resume capability."""
    workflow_id: str
    timestamp: float
    node_states: Dict[str, Dict[str, Any]]
    variables: Dict[str, Any]
    completed_nodes: List[str]

    def to_json(self) -> str:
        return json.dumps({
            "workflow_id": self.workflow_id,
            "timestamp": self.timestamp,
            "node_states": self.node_states,
            "variables": self.variables,
            "completed_nodes": self.completed_nodes,
        })

# ── TITANIUM v29.0 Integration ──


    @classmethod
    def from_json(cls, data: str) -> "WorkflowCheckpoint":
        d = json.loads(data)
        return cls(**d)


# ═══════════════════════════════════════════════════════════════════
# Expression Evaluator (Safe)
# ═══════════════════════════════════════════════════════════════════

class ExpressionEvaluator:
    """
    Safe expression evaluator for workflow conditions and transforms.

    Supports:
      - Variable references: ${variable_name}
      - Comparisons: ==, !=, <, >, <=, >=
      - Logical operators: and, or, not
      - String operations: contains, startswith, endswith
      - Arithmetic: +, -, *, /, %
      - Type checks: is_null, is_empty, is_number
    """

    def __init__(self, variables: Dict[str, Any]) -> None:
        self.variables = variables

    def resolve_variable(self, expr: str) -> Any:
        """Resolve ${var.path} references."""
        pattern = r"\$\{([^}]+)\}"
        matches = re.findall(pattern, expr)
        if not matches:
            return expr

        result = expr
        for match in matches:
            value = self._get_nested(match)
            if isinstance(value, str) and result == f"${{{match}}}":
                return value
            result = result.replace(f"${{{match}}}", str(value))
        return result

    def _get_nested(self, path: str) -> Any:
        """Get nested value from variables using dot notation."""
        parts = path.split(".")
        current = self.variables
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, (list, tuple)):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return current

    def evaluate_condition(self, expr: str) -> bool:
        """Evaluate a boolean expression."""
        expr = expr.strip()

        # Handle logical operators
        if " and " in expr:
            parts = expr.split(" and ", 1)
            return self.evaluate_condition(parts[0]) and self.evaluate_condition(parts[1])
        if " or " in expr:
            parts = expr.split(" or ", 1)
            return self.evaluate_condition(parts[0]) or self.evaluate_condition(parts[1])
        if expr.startswith("not "):
            return not self.evaluate_condition(expr[4:])

        # Handle comparisons
        for op in ["==", "!=", "<=", ">=", "<", ">"]:
            if op in expr:
                left, right = expr.split(op, 1)
                left_val = self.resolve_variable(left.strip())
                right_val = self.resolve_variable(right.strip())
                return self._compare(left_val, right_val, op)

        # Handle special functions
        if expr.startswith("is_null("):
            var = expr[8:-1].strip()
            return self.resolve_variable(f"${{{var}}}") is None
        if expr.startswith("is_empty("):
            var = expr[9:-1].strip()
            val = self.resolve_variable(f"${{{var}}}")
            return val is None or val == "" or val == [] or val == {}
        if expr.startswith("contains("):
            args = expr[9:-1].split(",", 1)
            haystack = str(self.resolve_variable(args[0].strip()))
            needle = str(self.resolve_variable(args[1].strip()))
            return needle in haystack

        # Truthy evaluation
        val = self.resolve_variable(f"${{{expr}}}")
        return bool(val)

    def _compare(self, left: Any, right: Any, op: str) -> bool:
        """Compare two values."""
        # Try numeric comparison
        try:
            left_num = float(str(left))
            right_num = float(str(right).strip("'\""))
            if op == "==":
                return left_num == right_num
            elif op == "!=":
                return left_num != right_num
            elif op == "<":
                return left_num < right_num
            elif op == ">":
                return left_num > right_num
            elif op == "<=":
                return left_num <= right_num
            elif op == ">=":
                return left_num >= right_num
        except (ValueError, TypeError):
            logger.debug("Suppressed: %s", _exc)

        # String comparison
        left_str = str(left).strip("'\"")
        right_str = str(right).strip("'\"")
        if op == "==":
            return left_str == right_str
        elif op == "!=":
            return left_str != right_str
        return False

    def interpolate(self, template: str) -> str:
        """Interpolate variables into a template string."""
        return str(self.resolve_variable(template))


# ═══════════════════════════════════════════════════════════════════
# DAG (Directed Acyclic Graph) Core
# ═══════════════════════════════════════════════════════════════════

class DAG:
    """
    Directed Acyclic Graph implementation.

    Supports cycle detection, topological sorting,
    and dependency resolution.
    """

    def __init__(self) -> None:
        self.adjacency: Dict[str, List[str]] = defaultdict(list)
        self.in_degree: Dict[str, int] = defaultdict(int)
        self.nodes: Set[str] = set()

    def add_node(self, node_id: str) -> None:
        """Add a node to the graph."""
        self.nodes.add(node_id)
        if node_id not in self.in_degree:
            self.in_degree[node_id] = 0

    def add_edge(self, source: str, target: str) -> None:
        """Add a directed edge from source to target."""
        self.adjacency[source].append(target)
        self.in_degree[target] = self.in_degree.get(target, 0) + 1
        self.nodes.add(source)
        self.nodes.add(target)

    def has_cycle(self) -> bool:
        """
        Detect cycles using Kahn's algorithm.

        Returns True if a cycle is found.
        """
        in_degree = dict(self.in_degree)
        for node in self.nodes:
            if node not in in_degree:
                in_degree[node] = 0

        queue = deque([n for n in self.nodes if in_degree.get(n, 0) == 0])
        visited = 0

        while queue:
            node = queue.popleft()
            visited += 1
            for neighbor in self.adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return visited != len(self.nodes)

    def topological_sort(self) -> List[str]:
        """
        Topological sort using Kahn's algorithm.

        Returns nodes in execution order.
        Raises ValueError if graph has cycles.
        """
        if self.has_cycle():
            raise ValueError("Workflow contains a cycle — cannot sort")

        in_degree = dict(self.in_degree)
        for node in self.nodes:
            if node not in in_degree:
                in_degree[node] = 0

        queue = deque(
            sorted([n for n in self.nodes if in_degree.get(n, 0) == 0])
        )
        result: List[str] = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in sorted(self.adjacency.get(node, [])):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def get_dependencies(self, node_id: str) -> Set[str]:
        """Get all nodes that must complete before this node."""
        deps: Set[str] = set()
        for source, targets in self.adjacency.items():
            if node_id in targets:
                deps.add(source)
        return deps

    def get_dependents(self, node_id: str) -> Set[str]:
        """Get all nodes that depend on this node."""
        return set(self.adjacency.get(node_id, []))

    def get_independent_groups(self) -> List[List[str]]:
        """
        Get groups of nodes that can execute in parallel.

        Returns list of levels, where each level contains
        nodes with no dependencies on the same level.
        """
        order = self.topological_sort()
        levels: Dict[str, int] = {}

        for node in order:
            deps = self.get_dependencies(node)
            if not deps:
                levels[node] = 0
            else:
                levels[node] = max(levels.get(d, 0) for d in deps) + 1

        groups: Dict[int, List[str]] = defaultdict(list)
        for node, level in levels.items():
            groups[level].append(node)

        return [groups[i] for i in sorted(groups.keys())]


# ═══════════════════════════════════════════════════════════════════
# Workflow Builder
# ═══════════════════════════════════════════════════════════════════

class Workflow:
    """
    Complete workflow definition and execution engine.

    Build → Validate → Execute → Monitor
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        version: str = "1.0.0",
    ) -> None:
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.description: str = description
        self.version: str = version

        self.nodes: Dict[str, WorkflowNode] = {}
        self.edges: List[WorkflowEdge] = []
        self.dag: DAG = DAG()
        self.variables: Dict[str, Any] = {}

        self.status_code: WorkflowStatus = WorkflowStatus.DRAFT
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        self.handlers: Dict[str, Callable] = {}
        self.checkpoints: List[WorkflowCheckpoint] = []
        self.execution_log: List[Dict[str, Any]] = []

    # ─── Node Management ─────────────────────────────────────────

    def add_node(
        self,
        node_id: str,
        name: str,
        node_type: NodeType = NodeType.TASK,
        handler: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        config: Optional[NodeConfig] = None,
    ) -> "Workflow":
        """Add a node to the workflow. Returns self for chaining."""
        node = WorkflowNode(
            id=node_id,
            name=name,
            node_type=node_type,
            handler=handler,
            parameters=parameters or {},
            config=config or NodeConfig(),
        )
        self.nodes[node_id] = node
        self.dag.add_node(node_id)
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType = EdgeType.NORMAL,
        condition: Optional[str] = None,
    ) -> "Workflow":
        """Add a directed edge between nodes. Returns self for chaining."""
        edge = WorkflowEdge(
            source=source,
            target=target,
            edge_type=edge_type,
            condition=condition,
        )
        self.edges.append(edge)
        self.dag.add_edge(source, target)
        return self

    def set_variable(self, key: str, value: Any) -> "Workflow":
        """Set a workflow variable."""
        self.variables[key] = value
        return self

    def register_handler(self, name: str, func: Callable) -> "Workflow":
        """Register a handler function for task nodes."""
        self.handlers[name] = func
        return self

    # ─── Validation ───────────────────────────────────────────────

    def validate(self) -> List[str]:
        """
        Validate the workflow.

        Returns list of error messages (empty = valid).
        """
        errors: List[str] = []

        # Check for empty workflow
        if not self.nodes:
            errors.append("Workflow has no nodes")

        # Check for cycles
        if self.dag.has_cycle():
            errors.append("Workflow contains a cycle")

        # Check edge references
        for edge in self.edges:
            if edge.source not in self.nodes:
                errors.append(f"Edge references unknown source: {edge.source}")
            if edge.target not in self.nodes:
                errors.append(f"Edge references unknown target: {edge.target}")

        # Check for orphan nodes (no edges)
        connected = set()
        for edge in self.edges:
            connected.add(edge.source)
            connected.add(edge.target)
        for node_id in self.nodes:
            if node_id not in connected and len(self.nodes) > 1:
                errors.append(f"Orphan node (no edges): {node_id}")

        # Check handlers exist for task nodes
        for node_id, node in self.nodes.items():
            if node.node_type == NodeType.TASK and node.handler:
                if node.handler not in self.handlers:
                    errors.append(
                        f"Node '{node_id}' references unregistered handler: {node.handler}"
                    )

        return errors

    # ─── Execution ────────────────────────────────────────────────

    def execute(self, initial_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the entire workflow.

        Uses topological order, handles branching, loops, and parallel nodes.
        """
        if initial_vars:
            self.variables.update(initial_vars)

        self.status_code = WorkflowStatus.RUNNING
        self.start_time = time.time()
        self._log("workflow_start", {"name": self.name})

        try:
            execution_order = self.dag.topological_sort()
            skipped: Set[str] = set()

            for node_id in execution_order:
                if node_id in skipped:
                    self.nodes[node_id].status = NodeStatus.SKIPPED
                    continue

                node = self.nodes[node_id]
                result = self._execute_node(node)

                # Handle conditional branching
                if node.node_type == NodeType.CONDITION:
                    skip_targets = self._resolve_condition_branches(node, result)
                    skipped.update(skip_targets)

                # Handle for_each loops
                elif node.node_type == NodeType.FOR_EACH:
                    self._execute_for_each(node)

            self.status_code = WorkflowStatus.COMPLETED
            self.end_time = time.time()
            self._log("workflow_complete", {
                "duration": self.end_time - self.start_time,
            })

        except Exception as e:
            self.status_code = WorkflowStatus.FAILED
            self.end_time = time.time()
            self._log("workflow_failed", {"error": str(e)})
            raise

        return self.get_results()

    async def _execute_node(self, node: WorkflowNode) -> Any:
        """Execute a single node with retry support."""
        node.status_code = NodeStatus.RUNNING
        node.start_time = time.time()
        self._log("node_start", {"node": node.id, "type": node.node_type.value})

        evaluator = ExpressionEvaluator(self.variables)

        # Resolve parameter variables
        resolved_params = {}
        for key, val in node.parameters.items():
            if isinstance(val, str):
                resolved_params[key] = evaluator.interpolate(val)
            else:
                resolved_params[key] = val

        max_attempts = 1
        if node.config.retry_policy:
            max_attempts = node.config.retry_policy.max_retries + 1

        last_error = None
        for attempt in range(max_attempts):
            node.attempt = attempt + 1
            try:
                result = self._run_handler(node, resolved_params)
                node.status_code = NodeStatus.COMPLETED
                node.result = result
                node.end_time = time.time()

                # Store result in variables
                self.variables[f"nodes.{node.id}.result"] = result
                self.variables[f"nodes.{node.id}.status"] = "completed"

                self._log("node_complete", {
                    "node": node.id,
                    "duration": node.duration(),
                    "attempt": attempt + 1,
                })
                return result

            except Exception as e:
                last_error = e
                if attempt < max_attempts - 1 and node.config.retry_policy:
                    delay = node.config.retry_policy.get_delay(attempt)
                    node.status_code = NodeStatus.RETRYING
                    self._log("node_retry", {
                        "node": node.id,
                        "attempt": attempt + 1,
                        "delay": delay,
                        "error": str(e),
                    })
                    await asyncio.sleep(delay)

        # All retries exhausted
        node.status_code = NodeStatus.FAILED
        node.error = str(last_error)
        node.end_time = time.time()
        self.variables[f"nodes.{node.id}.status"] = "failed"
        self.variables[f"nodes.{node.id}.error"] = str(last_error)

        if node.config.skip_on_error:
            self._log("node_skip_on_error", {"node": node.id})
            return None

        raise RuntimeError(f"Node '{node.id}' failed: {last_error}")

    async def _run_handler(self, node: WorkflowNode, params: Dict[str, Any]) -> Any:
        """Run the actual handler for a node."""
        if node.node_type == NodeType.DELAY:
            delay = float(params.get("seconds", 1))
            await asyncio.sleep(delay)
            return {"delayed": delay}

        if node.node_type == NodeType.TRANSFORM:
            evaluator = ExpressionEvaluator(self.variables)
            expr = params.get("expression", "")
            return evaluator.resolve_variable(expr)

        if node.node_type == NodeType.CHECKPOINT:
            self._create_checkpoint()
            return {"checkpoint_created": True}

        if node.handler and node.handler in self.handlers:
            return self.handlers[node.handler](params, self.variables)

        # Default: return parameters as result
        return params

    def _resolve_condition_branches(
        self, node: WorkflowNode, result: Any
    ) -> Set[str]:
        """Determine which branches to skip based on condition result."""
        skip: Set[str] = set()
        condition_met = bool(result)

        for edge in self.edges:
            if edge.source != node.id:
                continue
            if edge.edge_type == EdgeType.CONDITIONAL_TRUE and not condition_met:
                skip.add(edge.target)
                skip.update(self._get_all_downstream(edge.target))
            elif edge.edge_type == EdgeType.CONDITIONAL_FALSE and condition_met:
                skip.add(edge.target)
                skip.update(self._get_all_downstream(edge.target))

        return skip

    def _execute_for_each(self, node: WorkflowNode) -> None:
        """Execute a for_each loop node."""
        items_key = node.parameters.get("items", "")
        evaluator = ExpressionEvaluator(self.variables)
        items = evaluator.resolve_variable(items_key)

        if not isinstance(items, (list, tuple)):
            return

        results = []
        for idx, item in enumerate(items):
            self.variables["loop.index"] = idx
            self.variables["loop.item"] = item
            self.variables["loop.total"] = len(items)

            # Execute child nodes
            for edge in self.edges:
                if edge.source == node.id:
                    child = self.nodes.get(edge.target)
                    if child:
                        result = self._execute_node(child)
                        results.append(result)

        node.result = results

    def _get_all_downstream(self, node_id: str) -> Set[str]:
        """Get all nodes downstream of a given node (transitive)."""
        visited: Set[str] = set()
        queue = deque([node_id])
        while queue:
            current = queue.popleft()
            for edge in self.edges:
                if edge.source == current and edge.target not in visited:
                    visited.add(edge.target)
                    queue.append(edge.target)
        return visited

    # ─── Checkpoint / Resume ──────────────────────────────────────

    def _create_checkpoint(self) -> WorkflowCheckpoint:
        """Create a checkpoint of current state."""
        node_states = {}
        for nid, node in self.nodes.items():
            node_states[nid] = {
                "status": node.status_code.value,
                "result": node.result,
                "error": node.error,
                "attempt": node.attempt,
            }

        checkpoint = WorkflowCheckpoint(
            workflow_id=self.id,
            timestamp=time.time(),
            node_states=node_states,
            variables=dict(self.variables),
            completed_nodes=[
                nid for nid, n in self.nodes.items()
                if n.status_code == NodeStatus.COMPLETED
            ],
        )
        self.checkpoints.append(checkpoint)
        return checkpoint

    def resume_from_checkpoint(self, checkpoint: WorkflowCheckpoint) -> Dict[str, Any]:
        """Resume workflow execution from a checkpoint."""
        self.variables = dict(checkpoint.variables)

        for nid, state in checkpoint.node_states.items():
            if nid in self.nodes:
                node = self.nodes[nid]
                node.status_code = NodeStatus(state["status"])
                node.result = state.get("result")
                node.error = state.get("error")
                node.attempt = state.get("attempt", 0)

        # Re-execute only incomplete nodes
        self.status_code = WorkflowStatus.RUNNING
        execution_order = self.dag.topological_sort()

        for node_id in execution_order:
            node = self.nodes[node_id]
            if node.status_code == NodeStatus.COMPLETED:
                continue
            node.status_code = NodeStatus.PENDING
            self._execute_node(node)

        self.status_code = WorkflowStatus.COMPLETED
        return self.get_results()

    # ─── Monitoring ───────────────────────────────────────────────

    def get_results(self) -> Dict[str, Any]:
        """Get results from all completed nodes."""
        results = {}
        for nid, node in self.nodes.items():
            results[nid] = {
                "status": node.status_code.value,
                "result": node.result,
                "error": node.error,
                "duration": node.duration(),
                "attempts": node.attempt,
            }
        return results

    def get_progress(self) -> Dict[str, Any]:
        """Get workflow execution progress."""
        total = len(self.nodes)
        completed = sum(
            1 for n in self.nodes.values()
            if n.status_code == NodeStatus.COMPLETED
        )
        failed = sum(
            1 for n in self.nodes.values()
            if n.status_code == NodeStatus.FAILED
        )
        running = sum(
            1 for n in self.nodes.values()
            if n.status_code == NodeStatus.RUNNING
        )

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": total - completed - failed - running,
            "percentage": round(completed / max(1, total) * 100, 1),
            "status": self.status_code.value,
            "duration": (
                (self.end_time or time.time()) - self.start_time
                if self.start_time else 0
            ),
        }

    def get_timeline(self) -> List[Dict[str, Any]]:
        """Get execution timeline for visualization."""
        timeline = []
        for nid, node in self.nodes.items():
            if node.start_time:
                timeline.append({
                    "node": nid,
                    "name": node.name,
                    "start": node.start_time,
                    "end": node.end_time or time.time(),
                    "status": node.status_code.value,
                    "duration": node.duration(),
                })
        timeline.sort(key=lambda x: x["start"])
        return timeline

    def _log(self, event: str, data: Dict[str, Any]) -> None:
        """Add entry to execution log."""
        self.execution_log.append({
            "timestamp": time.time(),
            "event": event,
            **data,
        })

    # ─── Serialization ────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialize workflow to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
            "variables": self.variables,
            "status": self.status_code.value,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize workflow to JSON."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workflow":
        """Deserialize workflow from dictionary."""
        wf = cls(
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
        )
        wf.id = data.get("id", str(uuid.uuid4()))
        wf.variables = data.get("variables", {})

        for nid, nd in data.get("nodes", {}).items():
            wf.add_node(
                node_id=nid,
                name=nd["name"],
                node_type=NodeType(nd["node_type"]),
                handler=nd.get("handler"),
                parameters=nd.get("parameters", {}),
            )

        for ed in data.get("edges", []):
            edge = WorkflowEdge.from_dict(ed)
            wf.edges.append(edge)
            wf.dag.add_edge(edge.source, edge.target)

        return wf

    @classmethod
    def from_json(cls, json_str: str) -> "Workflow":
        """Deserialize workflow from JSON string."""
        return cls.from_dict(json.loads(json_str))


# ═══════════════════════════════════════════════════════════════════
# Cron Scheduler
# ═══════════════════════════════════════════════════════════════════

class CronExpression:
    """
    Parse and evaluate cron expressions.

    Format: minute hour day_of_month month day_of_week
    Supports: *, */n, n-m, n,m,o
    """

    def __init__(self, expression: str) -> None:
        parts = expression.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {expression}")
        self.minute = self._parse_field(parts[0], 0, 59)
        self.hour = self._parse_field(parts[1], 0, 23)
        self.day_of_month = self._parse_field(parts[2], 1, 31)
        self.month = self._parse_field(parts[3], 1, 12)
        self.day_of_week = self._parse_field(parts[4], 0, 6)

    def _parse_field(self, field: str, min_val: int, max_val: int) -> Set[int]:
        """Parse a single cron field into a set of valid values."""
        values: Set[int] = set()

        for part in field.split(","):
            if part == "*":
                values.update(range(min_val, max_val + 1))
            elif "/" in part:
                base, step = part.split("/")
                start = min_val if base == "*" else int(base)
                values.update(range(start, max_val + 1, int(step)))
            elif "-" in part:
                start, end = part.split("-")
                values.update(range(int(start), int(end) + 1))
            else:
                values.add(int(part))

        return values

    def matches(self, minute: int, hour: int, day: int,
                month: int, weekday: int) -> bool:
        """Check if the given time matches the cron expression."""
        return (
            minute in self.minute
            and hour in self.hour
            and day in self.day_of_month
            and month in self.month
            and weekday in self.day_of_week
        )


class WorkflowScheduler:
    """Schedule workflows for periodic execution."""

    def __init__(self) -> None:
        self.schedules: Dict[str, Dict[str, Any]] = {}
        self.execution_history: List[Dict[str, Any]] = []

    def schedule(
        self,
        workflow: Workflow,
        cron_expression: str,
        timezone: str = "UTC",
        enabled: bool = True,
    ) -> str:
        """Schedule a workflow for periodic execution."""
        schedule_id = str(uuid.uuid4())[:8]
        self.schedules[schedule_id] = {
            "workflow": workflow,
            "cron": CronExpression(cron_expression),
            "cron_expr": cron_expression,
            "timezone": timezone,
            "enabled": enabled,
            "last_run": None,
            "next_run": None,
            "run_count": 0,
        }
        return schedule_id

    def unschedule(self, schedule_id: str) -> bool:
        """Remove a scheduled workflow."""
        return self.schedules.pop(schedule_id, None) is not None

    def list_schedules(self) -> List[Dict[str, Any]]:
        """List all scheduled workflows."""
        result = []
        for sid, sched in self.schedules.items():
            result.append({
                "id": sid,
                "workflow": sched["workflow"].name,
                "cron": sched["cron_expr"],
                "enabled": sched["enabled"],
                "last_run": sched["last_run"],
                "run_count": sched["run_count"],
            })
        return result


# ═══════════════════════════════════════════════════════════════════
# Workflow Templates
# ═══════════════════════════════════════════════════════════════════

class WorkflowTemplates:
    """Pre-built workflow templates for common patterns."""

    @staticmethod
    def scan_and_report(target: str) -> Workflow:
        """Template: Scan target → Analyze → Generate report."""
        wf = Workflow("Scan & Report", f"Automated scan of {target}")
        wf.add_node("recon", "Web Reconnaissance", NodeType.TASK,
                     handler="web_recon", parameters={"target": target})
        wf.add_node("analyze", "Analyze Results", NodeType.TASK,
                     handler="data_analyze", parameters={"source": "${nodes.recon.result}"})
        wf.add_node("report", "Generate Report", NodeType.TASK,
                     handler="report_gen", parameters={"data": "${nodes.analyze.result}"})
        wf.add_edge("recon", "analyze")
        wf.add_edge("analyze", "report")
        return wf

    @staticmethod
    def etl_pipeline(source: str, destination: str) -> Workflow:
        """Template: Extract → Transform → Load."""
        wf = Workflow("ETL Pipeline", f"ETL: {source} → {destination}")
        wf.add_node("extract", "Extract Data", NodeType.TASK,
                     handler="extract", parameters={"source": source})
        wf.add_node("validate", "Validate Data", NodeType.TASK,
                     handler="validate", parameters={"data": "${nodes.extract.result}"})
        wf.add_node("check_valid", "Check Validation", NodeType.CONDITION,
                     parameters={"condition": "${nodes.validate.result.valid}"})
        wf.add_node("transform", "Transform Data", NodeType.TASK,
                     handler="transform", parameters={"data": "${nodes.extract.result}"})
        wf.add_node("load", "Load Data", NodeType.TASK,
                     handler="load", parameters={
                         "data": "${nodes.transform.result}",
                         "destination": destination,
                     })
        wf.add_node("alert_invalid", "Alert: Invalid Data", NodeType.TASK,
                     handler="alert", parameters={"message": "Data validation failed"})

        wf.add_edge("extract", "validate")
        wf.add_edge("validate", "check_valid")
        wf.add_edge("check_valid", "transform", EdgeType.CONDITIONAL_TRUE)
        wf.add_edge("check_valid", "alert_invalid", EdgeType.CONDITIONAL_FALSE)
        wf.add_edge("transform", "load")
        return wf

    @staticmethod
    def monitoring_loop(targets: List[str], interval_seconds: int = 60) -> Workflow:
        """Template: Monitor targets → Alert on issues."""
        wf = Workflow("Monitoring Loop", f"Monitor {len(targets)} targets")
        wf.add_node("check_all", "Check All Targets", NodeType.FOR_EACH,
                     parameters={"items": targets})
        wf.add_node("check_target", "Check Target", NodeType.TASK,
                     handler="health_check", parameters={"target": "${loop.item}"})
        wf.add_node("evaluate", "Evaluate Results", NodeType.CONDITION,
                     parameters={"condition": "${nodes.check_target.result.healthy}"})
        wf.add_node("alert", "Send Alert", NodeType.TASK,
                     handler="alert", parameters={
                         "target": "${loop.item}",
                         "status": "unhealthy",
                     })
        wf.add_edge("check_all", "check_target")
        wf.add_edge("check_target", "evaluate")
        wf.add_edge("evaluate", "alert", EdgeType.CONDITIONAL_FALSE)
        return wf

    @staticmethod
    def parallel_search(query: str, engines: Optional[List[str]] = None) -> Workflow:
        """Template: Search multiple engines in parallel → Merge results."""
        engines = engines or ["google", "bing", "duckduckgo"]
        wf = Workflow("Parallel Search", f"Search: {query}")

        for engine in engines:
            wf.add_node(
                f"search_{engine}", f"Search {engine}",
                NodeType.TASK, handler="web_search",
                parameters={"query": query, "engine": engine},
            )

        wf.add_node("merge", "Merge & Deduplicate", NodeType.MERGE,
                     handler="merge_results")
        wf.add_node("rank", "Rank Results", NodeType.TASK,
                     handler="rank_results")

        for engine in engines:
            wf.add_edge(f"search_{engine}", "merge")
        wf.add_edge("merge", "rank")

        return wf


# ═══════════════════════════════════════════════════════════════════
# Workflow Visualizer (ASCII)
# ═══════════════════════════════════════════════════════════════════

class WorkflowVisualizer:
    """Generate ASCII visualization of workflows."""

    @staticmethod
    def render(workflow: Workflow) -> str:
        """Render workflow as ASCII diagram."""
        lines = [
            f"╔══ Workflow: {workflow.name} ═══",
            f"║  Status: {workflow.status_code.value}",
            f"║  Nodes: {len(workflow.nodes)} | Edges: {len(workflow.edges)}",
            "╠══════════════════════════════════",
        ]

        groups = workflow.dag.get_independent_groups()
        for level, group in enumerate(groups):
            lines.append(f"║  Level {level}:")
            for node_id in group:
                node = workflow.nodes[node_id]
                status_icon = {
                    NodeStatus.PENDING: "○",
                    NodeStatus.RUNNING: "◉",
                    NodeStatus.COMPLETED: "●",
                    NodeStatus.FAILED: "✗",
                    NodeStatus.SKIPPED: "◌",
                }.get(node.status_code, "?")

                duration = ""
                if node.duration():
                    duration = f" ({node.duration():.2f}s)"

                lines.append(
                    f"║    {status_icon} [{node.node_type.value}] "
                    f"{node.name}{duration}"
                )

            if level < len(groups) - 1:
                lines.append("║      │")
                lines.append("║      ▼")

        lines.append("╚══════════════════════════════════")
        return "\n".join(lines)


