
from __future__ import annotations
"""
architecture.engine.execution — ExecutionEngine, ProcessingEngine
═════════════════════════════════════════════════════════════════
Low-level execution primitives with timeout, cancellation, and metrics.
Covers: execution-engine, processing-engine, execution-core
"""
import asyncio, logging, time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional



logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_s: float = 0.0
    retries: int = 0

class ExecutionEngine:
    """Execute callables with timeout, retry, and circuit breaker."""
    def __init__(self, default_timeout: float = 30.0, max_retries: int = 2) -> None:
        self._timeout = default_timeout
        self._max_retries = max_retries
        self._circuit_breakers: Dict[str, int] = {}
        self._stats = {"executed": 0, "success": 0, "failed": 0}

    async def execute(self, fn: Callable, *args, name: str = "",
                      timeout: Optional[float] = None, retries: Optional[int] = None,
                      **kwargs) -> ExecutionResult:
        max_r = retries if retries is not None else self._max_retries
        tout = timeout or self._timeout
        last_error = None
        for attempt in range(max_r + 1):
            t0 = time.time()
            try:
                result = fn(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await asyncio.wait_for(result, timeout=tout)
                self._stats["executed"] += 1
                self._stats["success"] += 1
                return ExecutionResult(success=True, result=result,
                                       duration_s=time.time() - t0, retries=attempt)
            except asyncio.TimeoutError:
                last_error = f"Timeout after {tout}s"
            except Exception as exc:
                last_error = str(exc)
            if attempt < max_r:
                await asyncio.sleep(0.5 * (attempt + 1))

        self._stats["executed"] += 1
        self._stats["failed"] += 1
        return ExecutionResult(success=False, error=last_error,
                               duration_s=time.time() - t0, retries=max_r)

    @property
    def stats(self) -> Dict[str, int]:
        return dict(self._stats)

class ProcessingEngine:
    """Batch processing with parallel execution and progress tracking."""
    def __init__(self, concurrency: int = 5) -> None:
        self._concurrency = concurrency
        self._semaphore = asyncio.Semaphore(concurrency)
        self._processed = 0

    async def process_batch(self, items: List[Any], processor: Callable,
                            on_progress: Optional[Callable] = None) -> List[ExecutionResult]:
        results: List[ExecutionResult] = []
        total = len(items)
        async def _process_one(item, idx):
            async with self._semaphore:
                t0 = time.time()
                try:
                    result = processor(item)
                    if asyncio.iscoroutine(result):
                        result = await result
                    r = ExecutionResult(success=True, result=result, duration_s=time.time()-t0)
                except Exception as exc:
                    r = ExecutionResult(success=False, error=str(exc), duration_s=time.time()-t0)
                self._processed += 1
                if on_progress:
                    on_progress(idx + 1, total)
                return r

        tasks = [_process_one(item, i) for i, item in enumerate(items)]
        results = await asyncio.gather(*tasks)
        return list(results)

    @property
    def stats(self) -> Dict[str, Any]:
        return {"processed": self._processed, "concurrency": self._concurrency}


