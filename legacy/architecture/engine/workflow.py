
from __future__ import annotations
"""
architecture.engine.workflow — WorkflowEngine
═══════════════════════════════════════════════
Multi-step workflow execution with branching, retries, and state tracking.
Covers: workflow-engine, workflow
"""
import asyncio, logging, time, uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional



logger = logging.getLogger(__name__)

class StepStatus(Enum):
    PENDING = auto(); RUNNING = auto(); SUCCESS = auto()
    FAILED = auto(); SKIPPED = auto(); RETRY = auto()

@dataclass
class WorkflowStep:
    name: str
    action: Callable
    depends_on: List[str] = field(default_factory=list)
    max_retries: int = 2
    timeout_s: float = 30.0
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    duration_s: float = 0.0
    retries: int = 0

@dataclass
class WorkflowRun:
    workflow_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    steps: List[WorkflowStep] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: str = "pending"
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return (self.end_time or time.time()) - self.start_time

class WorkflowEngine:
    """Execute multi-step workflows with dependency resolution."""
    def __init__(self) -> None:
        self._workflows: Dict[str, WorkflowRun] = {}
        self._templates: Dict[str, List[dict]] = {}

    def define_template(self, name: str, steps: List[dict]) -> None:
        self._templates[name] = steps

    def create(self, steps: Optional[List[WorkflowStep]] = None) -> WorkflowRun:
        run = WorkflowRun(steps=steps or [])
        self._workflows[run.workflow_id] = run
        return run

    def add_step(self, run: WorkflowRun, name: str, action: Callable,
                 depends_on: Optional[List[str]] = None, **kw) -> WorkflowStep:
        step = WorkflowStep(name=name, action=action, depends_on=depends_on or [], **kw)
        run.steps.append(step)
        return step

    async def execute(self, run: WorkflowRun) -> WorkflowRun:
        run.status = "running"
        completed = set()
        for step in run.steps:
            # Check dependencies
            unmet = [d for d in step.depends_on if d not in completed]
            if unmet:
                step.status = StepStatus.SKIPPED
                step.error = f"Unmet deps: {unmet}"
                continue
            # Execute with retries
            for attempt in range(step.max_retries + 1):
                t0 = time.time()
                try:
                    result = step.action(run.context)
                    if asyncio.iscoroutine(result):
                        result = await asyncio.wait_for(result, timeout=step.timeout_s)
                    step.result = result
                    step.status = StepStatus.SUCCESS
                    step.duration_s = time.time() - t0
                    run.context[f"step:{step.name}"] = result
                    completed.add(step.name)
                    break
                except Exception as exc:
                    step.retries = attempt + 1
                    step.error = str(exc)
                    step.duration_s = time.time() - t0
                    if attempt < step.max_retries:
                        step.status = StepStatus.RETRY
                        await asyncio.sleep(0.5 * (attempt + 1))
                    else:
                        step.status = StepStatus.FAILED
                        logger.error("Workflow step %s failed: %s", step.name, exc)

        run.end_time = time.time()
        failed = [s for s in run.steps if s.status == StepStatus.FAILED]
        run.status = "failed" if failed else "completed"
        return run

    def get_run(self, workflow_id: str) -> Optional[WorkflowRun]:
        return self._workflows.get(workflow_id)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_workflows": len(self._workflows),
            "templates": list(self._templates.keys()),
            "completed": sum(1 for w in self._workflows.values() if w.status == "completed"),
        }


