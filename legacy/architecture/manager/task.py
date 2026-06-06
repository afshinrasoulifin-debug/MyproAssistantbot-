
from __future__ import annotations
"""
architecture.manager.task — TaskManager, WorkflowManager, ProcessManager
═══════════════════════════════════════════════════════════════════════
Task lifecycle management with queuing, scheduling, and tracking.
Covers: task-manager, workflow-manager, process-manager, task, queue, action
"""
import logging, time, uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional



logger = logging.getLogger(__name__)

class TaskState(Enum):
    QUEUED = auto(); RUNNING = auto(); COMPLETED = auto()
    FAILED = auto(); CANCELLED = auto()

@dataclass
class ManagedTask:
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    state: TaskState = TaskState.QUEUED
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    priority: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)

class TaskManager:
    """Manage task lifecycle with priority queue."""
    def __init__(self) -> None:
        self._tasks: Dict[str, ManagedTask] = {}
        self._queue: List[ManagedTask] = []

    def create(self, name: str, priority: int = 5, **metadata) -> ManagedTask:
        task = ManagedTask(name=name, priority=priority, metadata=metadata)
        self._tasks[task.task_id] = task
        self._queue.append(task)
        self._queue.sort(key=lambda t: t.priority)
        return task

    def start(self, task_id: str) -> Optional[ManagedTask]:
        task = self._tasks.get(task_id)
        if task and task.state == TaskState.QUEUED:
            task.state = TaskState.RUNNING
            task.started_at = time.time()
            self._queue = [t for t in self._queue if t.task_id != task_id]
        return task

    def complete(self, task_id: str, result: Any = None) -> Optional[ManagedTask]:
        task = self._tasks.get(task_id)
        if task:
            task.state = TaskState.COMPLETED
            task.completed_at = time.time()
            task.result = result
        return task

    def fail(self, task_id: str, error: str) -> Optional[ManagedTask]:
        task = self._tasks.get(task_id)
        if task:
            task.state = TaskState.FAILED
            task.completed_at = time.time()
            task.error = error
        return task

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and task.state in (TaskState.QUEUED, TaskState.RUNNING):
            task.state = TaskState.CANCELLED
            return True
        return False

    def get_task(self, task_id: str) -> Optional[ManagedTask]:
        return self._tasks.get(task_id)

    def pending(self) -> List[ManagedTask]:
        return [t for t in self._tasks.values() if t.state == TaskState.QUEUED]

    def running(self) -> List[ManagedTask]:
        return [t for t in self._tasks.values() if t.state == TaskState.RUNNING]

    @property
    def stats(self) -> Dict[str, Any]:
        counts = {}
        for task in self._tasks.values():
            counts[task.state.name] = counts.get(task.state.name, 0) + 1
        return {"total": len(self._tasks), **counts}

class WorkflowManager(TaskManager):
    """Task manager with workflow support (sequential task chains)."""
    def __init__(self) -> None:
        super().__init__()
        self._chains: Dict[str, List[str]] = {}

    def create_chain(self, name: str, task_names: List[str]) -> List[ManagedTask]:
        tasks = [self.create(n) for n in task_names]
        self._chains[name] = [t.task_id for t in tasks]
        return tasks

    def next_in_chain(self, chain_name: str) -> Optional[ManagedTask]:
        ids = self._chains.get(chain_name, [])
        for tid in ids:
            task = self._tasks.get(tid)
            if task and task.state == TaskState.QUEUED:
                return task
        return None

class ProcessManager(TaskManager):
    """Task manager focused on long-running processes."""
    def __init__(self) -> None:
        super().__init__()
        self._progress: Dict[str, float] = {}

    def update_progress(self, task_id: str, progress: float) -> None:
        self._progress[task_id] = min(max(progress, 0), 100)

    def get_progress(self, task_id: str) -> float:
        return self._progress.get(task_id, 0)


