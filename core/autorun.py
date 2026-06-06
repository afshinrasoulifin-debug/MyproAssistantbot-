
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/core/autorun.py — Advanced Auto-Run & Orchestration Engine
═══════════════════════════════════════════════════════════════════
v9.0: Automated task scheduling, workflow chains, and proactive AI.

Features:
  • Scheduled task execution (cron-like)
  • Workflow chains (task A → task B → task C)
  • Proactive suggestions based on user patterns
  • Automated health checks and self-healing
  • Background analytics aggregation
  • Content scheduling (auto-post at optimal times)
"""


import asyncio
import traceback
import hashlib
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ScheduledTask:
    """A task scheduled for execution."""
    task_id: str
    name: str
    handler: str  # Handler function reference name
    params: Dict[str, Any] = field(default_factory=dict)
    schedule_cron: str = ""  # Cron expression
    interval_seconds: int = 0  # Simple interval
    next_run: float = 0.0
    last_run: float = 0.0
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass 
class WorkflowStep:
    """A single step in a workflow chain."""
    step_id: str
    name: str
    handler: str
    params: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None


@dataclass
class Workflow:
    """A chain of tasks that execute in order/parallel."""
    workflow_id: str
    name: str
    steps: List[WorkflowStep] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)


class AutoRunEngine:
    """
    Advanced auto-run orchestration engine.
    
    Manages:
    - Scheduled tasks (interval-based and cron-like)
    - Workflow chains with dependency resolution
    - Proactive user suggestions
    - Self-healing and health monitoring
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, ScheduledTask] = {}
        self._workflows: Dict[str, Workflow] = {}
        self._handlers: Dict[str, Callable] = {}
        self._user_patterns: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
            "commands_used": defaultdict(int),
            "active_hours": defaultdict(int),
            "last_active": 0,
            "total_interactions": 0,
        })
        self._running = False
        self._task: Optional[asyncio.Task] = None

    # ── Handler Registration ─────────────────────────────────

    def register_handler(self, name: str, handler: Callable) -> None:
        """Register a callable handler for tasks/workflows."""
        self._handlers[name] = handler
        logger.debug("AutoRun handler registered: %s", name)

    # ── Task Scheduling ──────────────────────────────────────

    def register_task(self, name: str, handler: Callable, interval_hours: float = 1) -> None:
        """Convenience: register handler + schedule in one call."""
        self.register_handler(name, handler)
        self.schedule_task(name, handler=name, interval_seconds=int(interval_hours * 3600))

    def schedule_task(
        self,
        name: str,
        handler: str,
        interval_seconds: int = 0,
        params: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> ScheduledTask:
        """Schedule a recurring task."""
        task_id = hashlib.md5(f"{name}:{time.time()}".encode()).hexdigest()[:10]
        
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            handler=handler,
            params=params or {},
            interval_seconds=interval_seconds,
            next_run=time.time() + interval_seconds,
            priority=priority,
        )
        self._tasks[task_id] = task
        logger.info("Task scheduled: %s (every %ds)", name, interval_seconds)
        return task

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.CANCELLED
            return True
        return False

    def get_tasks(self, status: Optional[TaskStatus] = None) -> List[ScheduledTask]:
        """Get all tasks, optionally filtered by status."""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.priority.value, reverse=True)

    # ── Workflow Management ───────────────────────────────────

    def create_workflow(
        self,
        name: str,
        steps: List[Dict[str, Any]],
    ) -> Workflow:
        """Create a workflow chain."""
        workflow_id = hashlib.md5(f"wf:{name}:{time.time()}".encode()).hexdigest()[:10]
        
        wf_steps = []
        for i, step_def in enumerate(steps):
            step = WorkflowStep(
                step_id=f"{workflow_id}_s{i}",
                name=step_def.get("name", f"Step {i+1}"),
                handler=step_def["handler"],
                params=step_def.get("params", {}),
                depends_on=step_def.get("depends_on", []),
            )
            wf_steps.append(step)
        
        workflow = Workflow(
            workflow_id=workflow_id,
            name=name,
            steps=wf_steps,
        )
        self._workflows[workflow_id] = workflow
        return workflow

    async def execute_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Execute a workflow, respecting step dependencies."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        
        workflow.status = TaskStatus.RUNNING
        completed_steps = set()
        
        for step in workflow.steps:
            # Check dependencies
            if step.depends_on:
                missing = [d for d in step.depends_on if d not in completed_steps]
                if missing:
                    step.status = TaskStatus.FAILED
                    step.result = f"Missing dependencies: {missing}"
                    continue
            
            # Execute step
            handler = self._handlers.get(step.handler)
            if not handler:
                step.status = TaskStatus.FAILED
                step.result = f"Handler not found: {step.handler}"
                continue
            
            try:
                step.status = TaskStatus.RUNNING
                result = await handler(**step.params)
                step.result = result
                step.status = TaskStatus.COMPLETED
                completed_steps.add(step.step_id)
            except ArkiBaseError as e:
                step.status = TaskStatus.FAILED
                step.result = str(e)
                logger.warning("Workflow step %s failed: %s", step.name, e)
        
        all_completed = all(s.status == TaskStatus.COMPLETED for s in workflow.steps)
        workflow.status = TaskStatus.COMPLETED if all_completed else TaskStatus.FAILED
        
        return workflow

    # ── User Pattern Analysis ────────────────────────────────

    def record_user_activity(
        self,
        user_id: int,
        command: str,
        hour: int = -1,
    ) -> None:
        """Record user activity for pattern analysis."""
        patterns = self._user_patterns[user_id]
        patterns["commands_used"][command] += 1
        patterns["total_interactions"] += 1
        patterns["last_active"] = time.time()
        
        if hour >= 0:
            patterns["active_hours"][hour] += 1

    def get_proactive_suggestions(self, user_id: int) -> List[Dict[str, str]]:
        """Generate proactive suggestions based on user patterns."""
        patterns = self._user_patterns.get(user_id)
        if not patterns or patterns["total_interactions"] < 5:
            return []
        
        suggestions = []
        commands = patterns["commands_used"]
        
        # Suggest related features based on usage
        if commands.get("search", 0) > 3 and not commands.get("deep", 0):
            suggestions.append({
                "type": "feature",
                "message": "💡 شما زیاد جستجو می‌کنید — /deep رو امتحان کنید برای تحقیق عمیق‌تر!",
            })
        
        if commands.get("content", 0) > 2 and not commands.get("batch", 0):
            suggestions.append({
                "type": "productivity",
                "message": "📅 با /batch می‌تونید یک هفته محتوا رو یکجا بسازید!",
            })
        
        if commands.get("caption", 0) > 3 and not commands.get("abtest", 0):
            suggestions.append({
                "type": "optimization",
                "message": "🧪 با /abtest کپشن‌ها رو A/B تست کنید تا بهترین رو پیدا کنید!",
            })
        
        if not commands.get("brand", 0) and patterns["total_interactions"] > 10:
            suggestions.append({
                "type": "setup",
                "message": "🏷 هنوز برند تنظیم نکردید — /brand بزنید تا محتواها شخصی‌سازی بشه!",
            })
        
        return suggestions

    # ── Background Runner ────────────────────────────────────

    async def start(self) -> None:
        """Start the auto-run background loop."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("AutoRun engine started")

    async def stop(self) -> None:
        """Stop the auto-run background loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError as _exc:
                logger.debug("Suppressed: %s", _exc)
        logger.info("AutoRun engine stopped")

    async def _run_loop(self) -> None:
        """Main background loop that checks and executes due tasks."""
        while self._running:
            now = time.time()
            
            for task_id, task in list(self._tasks.items()):
                if task.status == TaskStatus.CANCELLED:
                    continue
                
                if task.next_run <= now:
                    handler = self._handlers.get(task.handler)
                    if handler:
                        try:
                            task.status = TaskStatus.RUNNING
                            result = await handler(**task.params)
                            task.result = str(result)[:500] if result else "ok"
                            task.status = TaskStatus.COMPLETED
                            task.retry_count = 0
                        except ArkiBaseError as e:
                            task.error = str(e)
                            task.retry_count += 1
                            if task.retry_count >= task.max_retries:
                                task.status = TaskStatus.FAILED
                                logger.warning("Task %s failed after %d retries: %s",
                                             task.name, task.retry_count, e)
                            else:
                                task.status = TaskStatus.PENDING
                    
                    task.last_run = now
                    if task.interval_seconds > 0 and task.status != TaskStatus.FAILED:
                        task.next_run = now + task.interval_seconds
                        task.status = TaskStatus.PENDING
            
            await asyncio.sleep(10)  # Check every 10 seconds

    # ── Statistics ────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get auto-run engine statistics."""
        tasks = list(self._tasks.values())
        return {
            "total_tasks": len(tasks),
            "active": sum(1 for t in tasks if t.status == TaskStatus.PENDING),
            "running": sum(1 for t in tasks if t.status == TaskStatus.RUNNING),
            "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in tasks if t.status == TaskStatus.FAILED),
            "workflows": len(self._workflows),
            "monitored_users": len(self._user_patterns),
        }


# ── v9.1: Default scheduled tasks ──

async def register_default_tasks(engine: Any) -> None:
    """Register built-in scheduled tasks."""

    # Daily backup reminder
    async def daily_backup_check() -> Any:
        from arki_project.utils.alert_system import get_alert_system
        await get_alert_system().info("Backup Reminder", "روزانه: بکاپ دیتابیس انجام شود")

    # Hourly health check
    async def hourly_health() -> Any:
        from arki_project.utils.metrics_collector import get_metrics
        metrics = get_metrics()
        stats = metrics.get_all()
        uptime = stats.get("uptime_seconds", 0)
        errors = stats.get("counters", {}).get("errors_total", 0)
        if errors > 100:
            from arki_project.utils.alert_system import get_alert_system
            await get_alert_system().warning(
                "High Error Rate",
                f"خطاهای زیاد: {errors} خطا در {uptime/3600:.1f} ساعت"
            )

    # Memory cleanup
    async def memory_cleanup() -> Any:
        try:
            from arki_project.utils.v7_core import get_memory
            mem = get_memory()
            if hasattr(mem, '_cleanup'):
                mem._cleanup()
        except ArkiBaseError as _exc:
            logger.debug("Suppressed: %s", _exc)

    engine.register_task("daily_backup_check", daily_backup_check, interval_hours=24)
    engine.register_task("hourly_health", hourly_health, interval_hours=1)

    # v10.3: Victor brain health check
    async def victor_brain_check() -> Any:
        try:
            from arki_project.handlers.victor import VictorBrain
            brain = VictorBrain()
            stats = brain.memory.get_stats()
            logger.info("🧠 Victor brain: %d memories, avg_strength=%.1f",
                        stats.get("total_memories", 0), stats.get("avg_strength", 0))
        except ArkiBaseError as e:
            logger.debug("Victor brain check: %s", e)

    engine.register_task("victor_brain_check", victor_brain_check, interval_hours=6)
    engine.register_task("memory_cleanup", memory_cleanup, interval_hours=6)


# Daily analytics digest
async def analytics_digest() -> Any:
    """Generate daily analytics summary for admins."""
    try:
        from arki_project.utils.metrics_collector import get_metrics
        from arki_project.utils.alert_system import get_alert_system
        metrics = get_metrics()
        stats = metrics.get_all()
        counters = stats.get("counters", {})
        msg_total = sum(v for k, v in counters.items() if "messages" in k)
        err_total = sum(v for k, v in counters.items() if "errors" in k)
        await get_alert_system().info(
            "📊 گزارش روزانه",
            f"پیام‌ها: {msg_total:,}\nخطاها: {err_total:,}"
        )
    except ArkiBaseError as _exc:
        logger.debug("Suppressed: %s", _exc)

# Cache cleanup
async def cache_cleanup() -> Any:
    """Periodic cache cleanup."""
    try:
        from arki_project.utils.cache_layer import get_cache
        cache = get_cache()
        # Evict expired items
        import time
        expired = [k for k, ttl in cache._ttls.items() if time.time() > ttl]
        for k in expired:
            await cache.delete(k)
    except ArkiBaseError as _exc:
        logger.debug("Suppressed: %s", _exc)

# DB vacuum
async def db_vacuum() -> Any:
    """Periodic database vacuum for SQLite."""
    try:
        from arki_project.database.connection import get_session
        async with get_session() as session:
            await session.execute("VACUUM")
            await session.commit()
    except ArkiBaseError as _exc:
        logger.debug("Suppressed: %s", _exc)

# RAG index rebuild
async def rag_index_rebuild() -> Any:
    """Rebuild RAG search index."""
    try:
        from arki_project.utils.v7_core import get_memory
        mem = get_memory()
        if hasattr(mem, 'build_search_index'):
            mem.build_search_index()
    except ArkiBaseError as _exc:
        logger.debug("Suppressed: %s", _exc)

def register_extra_tasks(engine: Any) -> None:
    """Register additional maintenance tasks on an engine instance."""
    engine.register_task("analytics_digest", analytics_digest, interval_hours=24)
    engine.register_task("cache_cleanup", cache_cleanup, interval_hours=2)
    engine.register_task("db_vacuum", db_vacuum, interval_hours=48)
    engine.register_task("rag_index_rebuild", rag_index_rebuild, interval_hours=12)


# v9.4: Safe task wrapper with exception isolation
async def _safe_run(coro: Any, name: str = "unknown") -> Any:
    """Run a coroutine with proper exception handling."""
    try:
        return await coro
    except asyncio.CancelledError:
        logger.info("Task %s cancelled", name)
        raise
    except ArkiBaseError as e:
        logger.error("Background task %s failed: %s\n%s", name, e, traceback.format_exc())
        # Don't re-raise — isolate the failure
        return None


# v9.5: Data retention task
async def _data_retention_cleanup() -> Any:
    """Run data retention policy cleanup."""
    try:
        from arki_project.utils.data_retention import get_retention_manager
        mgr = get_retention_manager()
        await mgr.run_cleanup()
    except ArkiBaseError as e:
        logger.warning("Data retention cleanup failed: %s", e)

def register_data_retention_task(engine: Any) -> None:
    """Register data retention task on the given engine."""
    engine.register_task("data_retention", _data_retention_cleanup, interval_hours=24)


# v10.3.1: Auto-recovery for degraded services
async def _degradation_auto_recovery() -> Any:
    """Periodically probe degraded services and recover them."""
    try:
        from arki_project.utils.degradation import get_degradation_manager
        mgr = get_degradation_manager()
        results = await mgr.check_and_recover()
        recovered = [s for s, st in results.items() if st == "recovered"]
        if recovered:
            logger.info("🔄 Auto-recovery: %s", ", ".join(recovered))
    except ArkiBaseError as e:
        logger.debug("Auto-recovery check: %s", e)


def register_recovery_task(engine: Any) -> None:
    """Register degradation auto-recovery task (v10.3.1)."""
    engine.register_task("degradation_recovery", _degradation_auto_recovery, interval_hours=0.25)  # Every 15 min


_autorun_instance = None

def get_autorun_engine() -> Any:
    """Get or create the global AutoRun engine."""
    global _autorun_instance
    if _autorun_instance is None:
        _autorun_instance = AutoRunEngine()
    return _autorun_instance


