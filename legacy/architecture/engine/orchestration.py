
from __future__ import annotations
"""
architecture.engine.orchestration — OrchestrationEngine
═══════════════════════════════════════════════════════
Coordinates multiple engines and services for complex operations.
Covers: orchestration-engine, orchestrator, orchestration-core
"""
import asyncio, logging, time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple



logger = logging.getLogger(__name__)

@dataclass
class OrchestrationPlan:
    name: str
    stages: List[Tuple[str, Callable]] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"

class OrchestrationEngine:
    """Coordinate parallel and sequential execution of multiple operations."""
    def __init__(self) -> None:
        self._plans: Dict[str, OrchestrationPlan] = {}
        self._executors: Dict[str, Callable] = {}

    def register_executor(self, name: str, fn: Callable) -> None:
        self._executors[name] = fn

    def create_plan(self, name: str) -> OrchestrationPlan:
        plan = OrchestrationPlan(name=name)
        self._plans[name] = plan
        return plan

    def add_stage(self, plan: OrchestrationPlan, name: str, fn: Callable) -> None:
        plan.stages.append((name, fn))

    def add_parallel_group(self, plan: OrchestrationPlan, stage_names: List[str]) -> None:
        plan.parallel_groups.append(stage_names)

    async def execute_plan(self, plan: OrchestrationPlan, context: Optional[Dict] = None) -> Dict[str, Any]:
        ctx = context or {}
        plan.status = "running"
        stage_map = dict(plan.stages)

        # Execute parallel groups first
        for group in plan.parallel_groups:
            tasks = []
            for name in group:
                fn = stage_map.get(name)
                if fn:
                    tasks.append(self._run_stage(name, fn, ctx))
            if tasks:
                group_results = await asyncio.gather(*tasks, return_exceptions=True)
                for name, result in zip(group, group_results):
                    plan.results[name] = result if not isinstance(result, Exception) else str(result)
                    ctx[name] = plan.results[name]

        # Execute remaining sequential stages
        parallel_names = {n for g in plan.parallel_groups for n in g}
        for name, fn in plan.stages:
            if name in parallel_names or name in plan.results:
                continue
            plan.results[name] = await self._run_stage(name, fn, ctx)
            ctx[name] = plan.results[name]

        plan.status = "completed"
        return plan.results

    async def _run_stage(self, name: str, fn: Callable, ctx: Dict) -> Any:
        t0 = time.time()
        try:
            result = fn(ctx)
            if asyncio.iscoroutine(result):
                result = await result
            logger.debug("Stage %s completed in %.2fs", name, time.time() - t0)
            return result
        except Exception as exc:
            logger.error("Stage %s failed: %s", name, exc)
            return {"error": str(exc)}

    @property
    def stats(self) -> Dict[str, Any]:
        return {"plans": len(self._plans), "executors": list(self._executors.keys())}


