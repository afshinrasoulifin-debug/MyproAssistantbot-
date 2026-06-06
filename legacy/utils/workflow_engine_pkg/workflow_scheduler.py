
"""
workflow_engine_pkg/workflow_scheduler.py — WorkflowScheduler
Arki Engine v29.0.0
"""
from ._base import *  # noqa

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



