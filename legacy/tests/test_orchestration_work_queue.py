

import pytest
import asyncio
from unittest.mock import AsyncMock

from arki_project.orchestration.work_queue import WorkQueue
from arki_project.orchestration.types import RequestPriority

@pytest.mark.asyncio
class TestOrchestrationWorkQueue:

    async def test_work_queue_enqueue_dequeue(self):
        """C24: 5 آیتم enqueue، assert به ترتیب FIFO برگردند."""
        processed_items = []
        async def handler(payload):
            processed_items.append(payload)
            return payload

        queue = WorkQueue(max_workers=1)
        queue.set_handler(handler)
        await queue.start()

        for i in range(5):
            await queue.submit(f"item_{i}")

        # Give workers time to process
        await asyncio.sleep(0.1)
        await queue.stop()

        assert processed_items == [f"item_{i}" for i in range(5)]
        assert queue.stats()["total_completed"] == 5

    async def test_work_queue_priority_ordering(self):
        """C25: آیتم‌های HIGH/LOW/NORMAL، assert HIGH اول خارج شود."""
        processed_order = []
        async def handler(payload):
            await asyncio.sleep(0.01) # Simulate some work
            processed_order.append(payload)
            return payload

        queue = WorkQueue(max_workers=1)
        queue.set_handler(handler)
        await queue.start()

        # Submit items with different priorities
        await queue.submit("LOW_item", priority=RequestPriority.LOW)
        await queue.submit("HIGH_item", priority=RequestPriority.HIGH)
        await queue.submit("NORMAL_item", priority=RequestPriority.NORMAL)
        await queue.submit("CRITICAL_item", priority=RequestPriority.CRITICAL)

        # Give workers time to process all items
        await asyncio.sleep(0.5) # Sufficient time for all to be processed
        await queue.stop()

        # Assert that items are processed in priority order
        assert processed_order[0] == "CRITICAL_item"
        assert processed_order[1] == "HIGH_item"
        assert processed_order[2] == "NORMAL_item"
        assert processed_order[3] == "LOW_item"
        assert queue.stats()["total_completed"] == 4

    async def test_work_queue_max_size_blocks(self):
        """C26: queue پر، assert enqueue بیشتر block یا exception."""
        # Use a small queue size
        queue = WorkQueue(max_queue_size=2, max_workers=0) # No workers to process items
        await queue.start()

        # Enqueue up to max_queue_size
        await queue.submit("item1")
        await queue.submit("item2")

        # Attempt to enqueue one more item, which should raise QueueFull
        with pytest.raises(asyncio.QueueFull):
            await queue.submit("item3")

        await queue.stop()
        assert queue.stats()["total_rejected"] == 1
        assert queue.stats()["queue_size"] == 2

    async def test_work_queue_empty_get_raises_or_waits(self):
        """C27: queue خالی با timeout=0.1، assert asyncio.TimeoutError یا معادل."""
        queue = WorkQueue(max_workers=1) # Workers will try to get from empty queue
        queue.set_handler(AsyncMock(return_value="result"))
        await queue.start()

        # The queue is empty. submit_and_wait should eventually timeout.
        with pytest.raises(asyncio.TimeoutError):
            await queue.submit_and_wait("payload", timeout=0.1)

        await queue.stop()
        assert queue.stats()["total_rejected"] == 1 # Rejected due to timeout

    async def test_work_queue_concurrent_producers(self):
        """C28: 5 producer همزمان، assert هیچ آیتمی گم نشود."""
        processed_count = 0
        async def handler(payload):
            nonlocal processed_count
            await asyncio.sleep(0.001) # Simulate some work
            processed_count += 1
            return payload

        queue = WorkQueue(max_workers=5, max_queue_size=100)
        queue.set_handler(handler)
        await queue.start()

        num_producers = 5
        items_per_producer = 10
        total_items = num_producers * items_per_producer

        async def producer_task(producer_id):
            for i in range(items_per_producer):
                await queue.submit(f"producer_{producer_id}_item_{i}")

        producer_tasks = [producer_task(i) for i in range(num_producers)]
        await asyncio.gather(*producer_tasks)

        # Give workers time to process all items
        await asyncio.sleep(0.5) # Sufficient time for all to be processed
        await queue.stop()

        assert processed_count == total_items
        assert queue.stats()["total_completed"] == total_items
        assert queue.stats()["queue_size"] == 0



