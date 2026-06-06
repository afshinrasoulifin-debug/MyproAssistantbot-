
"""
agent_executor_pkg/step_scheduler.py — StepScheduler
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class StepScheduler:
    """
    DAG-based scheduler: runs independent steps in parallel,
    respects dependencies between steps.
    """

    def __init__(self, steps: List[AgentStep], max_parallel: int = PARALLEL_BATCH_SIZE):
        self._steps = {s.id: s for s in steps}
        self._max_parallel = max_parallel
        self._completed: Set[int] = set()
        self._failed: Set[int] = set()

    def get_ready_steps(self) -> List[AgentStep]:
        """Get steps whose dependencies are all completed."""
        ready = []
        for step in self._steps.values():
            if step.status not in (StepStatus.PENDING, StepStatus.QUEUED):
                continue
            # Check all dependencies are completed
            deps_met = all(d in self._completed for d in step.depends_on)
            deps_failed = any(d in self._failed for d in step.depends_on)
            if deps_failed:
                step.status = StepStatus.SKIPPED
                continue
            if deps_met:
                ready.append(step)
        return ready[:self._max_parallel]

    def mark_completed(self, step_id: int) -> None:
        self._completed.add(step_id)
        if step_id in self._steps:
            self._steps[step_id].status = StepStatus.COMPLETED

    def mark_failed(self, step_id: int) -> None:
        self._failed.add(step_id)
        if step_id in self._steps:
            self._steps[step_id].status = StepStatus.FAILED

    @property
    def all_done(self) -> bool:
        return all(
            s.status in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED)
            for s in self._steps.values()
        )


# ═══════════════════════════════════════════════════════════════════
# Agent Executor — Core Engine
# ═══════════════════════════════════════════════════════════════════



