
from __future__ import annotations
"""
tg_bot/utils/ai_batch.py — Batch AI Processing v9.3
Handles concurrent AI requests with rate limiting and deduplication.
"""
import asyncio
import hashlib
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════


logger = logging.getLogger(__name__)


@dataclass
class BatchItem:
    """Single item in a batch."""
    id: str
    prompt: str
    model: str = ""
    result: Optional[str] = None
    error: Optional[str] = None
    done: bool = False


class AIBatchProcessor:
    """
    Process multiple AI requests efficiently:
    - Concurrent execution with semaphore
    - Request deduplication
    - Retry on failure
    - Progress tracking
    """

    def __init__(self, max_concurrent: int = 5, max_retries: int = 2) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_retries = max_retries
        self._dedup_cache: Dict[str, str] = {}
        self._stats = {"total": 0, "completed": 0, "deduped": 0, "errors": 0}

    async def process_batch(
        self,
        items: List[Dict[str, str]],
        processor: Callable,
        on_progress: Optional[Callable] = None,
    ) -> List[BatchItem]:
        """
        Process a batch of AI requests.

        Args:
            items: List of {"prompt": "...", "model": "..."} dicts
            processor: async function(prompt, model) -> str
            on_progress: optional callback(completed, total)
        """
        batch_items = []
        for i, item in enumerate(items):
            prompt = item.get("prompt", "")
            model = item.get("model", "")
            batch_items.append(BatchItem(
                id=f"batch-{i}",
                prompt=prompt,
                model=model,
            ))

        self._stats["total"] += len(batch_items)
        tasks = [
            self._process_one(bi, processor, on_progress, len(batch_items))
            for bi in batch_items
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
        return batch_items

    async def _process_one(
        self, item: BatchItem, processor: Callable,
        on_progress: Optional[Callable], total: int
    ) -> Any:
        # Check dedup cache
        cache_key = hashlib.md5(f"{item.prompt}:{item.model}".encode()).hexdigest()
        if cache_key in self._dedup_cache:
            item.result = self._dedup_cache[cache_key]
            item.done = True
            self._stats["deduped"] += 1
            return

        async with self._semaphore:
            for attempt in range(self._max_retries + 1):
                try:
                    result = await processor(item.prompt, item.model)
                    item.result = result
                    item.done = True
                    self._dedup_cache[cache_key] = result
                    self._stats["completed"] += 1
                    break
                except Exception as e:
                    if attempt == self._max_retries:
                        item.error = str(e)
                        self._stats["errors"] += 1
                    else:
                        await asyncio.sleep(1 * (attempt + 1))

        if on_progress:
            completed = sum(1 for bi in [item] if bi.done)
            try:
                if asyncio.iscoroutinefunction(on_progress):
                    await on_progress(self._stats["completed"], total)
                else:
                    on_progress(self._stats["completed"], total)
            except Exception as _exc:
                logger.debug("Suppressed: %s", _exc)

    @property
    def stats(self) -> dict:
        return self._stats.copy()


_processor: Optional[AIBatchProcessor] = None

def get_batch_processor() -> AIBatchProcessor:
    global _processor
    if _processor is None:
        _processor = AIBatchProcessor()
    return _processor


