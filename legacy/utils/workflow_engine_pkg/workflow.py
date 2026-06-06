
"""
workflow_engine_pkg/workflow.py — Workflow
Arki Engine v29.0.0
"""
from ._base import *  # noqa

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



