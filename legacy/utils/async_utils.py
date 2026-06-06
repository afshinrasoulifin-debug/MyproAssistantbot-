
from __future__ import annotations
"""
utils/async_utils.py — Async Utilities & Patterns
═══════════════════════════════════════════════════
Non-blocking replacements for common synchronous operations.
"""

import asyncio
import functools
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")

# Shared thread pool for file I/O operations
_io_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="arki_io")


async def async_file_read(path: str, encoding: str = "utf-8") -> str:
    """Non-blocking file read."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_io_pool, functools.partial(
        _sync_read, path, encoding
    ))


def _sync_read(path: str, encoding: str) -> str:
    with open(path, encoding=encoding) as f:
        return f.read()


async def async_file_write(path: str, content: str, encoding: str = "utf-8") -> None:
    """Non-blocking file write."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_io_pool, functools.partial(
        _sync_write, path, content, encoding
    ))


def _sync_write(path: str, content: str, encoding: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding=encoding) as f:
        f.write(content)


async def run_sync(fn: Callable[..., T], *args, **kwargs) -> T:
    """Run a synchronous function in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _io_pool,
        functools.partial(fn, *args, **kwargs)
    )


class AsyncBatchProcessor:
    """Process items in batches with concurrency control."""

    def __init__(self, max_concurrency: int = 5, batch_size: int = 10) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._batch_size = batch_size

    async def process(self, items: list, handler: Callable) -> list:
        results = []
        for i in range(0, len(items), self._batch_size):
            batch = items[i:i + self._batch_size]
            batch_results = await asyncio.gather(*[
                self._guarded(handler, item) for item in batch
            ], return_exceptions=True)
            results.extend(batch_results)
        return results

    async def _guarded(self, handler: Any, item: Any) -> Any:
        async with self._semaphore:
            return await handler(item)


class AsyncTimer:
    """Async context manager for timing operations."""

    def __init__(self, name: str = "") -> None:
        self.name = name
        self.elapsed_ms: float = 0

    async def __aenter__(self) -> Any:
        self._start = asyncio.get_event_loop().time()
        return self

    async def __aexit__(self, *args) -> None:
        self.elapsed_ms = (asyncio.get_event_loop().time() - self._start) * 1000
        if self.name:
            logger.debug("%s: %.1fms", self.name, self.elapsed_ms)


