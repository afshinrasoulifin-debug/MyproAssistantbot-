

import pytest
import asyncio
from arki_project.orchestration.cache_layer import CacheLayer

@pytest.mark.asyncio
class TestOrchestrationCacheLayer:

    @pytest.fixture(autouse=True)
    def cache_layer_instance(self):
        """Provide a fresh CacheLayer instance for each test."""
        # Use a small max_size and ttl for testing purposes
        cache = CacheLayer(max_size=10, ttl=0.5) # TTL of 0.5 seconds
        yield cache
        cache.clear_all() # Clear cache after each test

    async def test_cache_set_and_get(self, cache_layer_instance: CacheLayer):
        """C33: مقدار set، بلافاصله get، assert مقدار صحیح."""
        key = "test_key"
        value = {"data": "some_value"}
        await cache_layer_instance.set_inference(key, value)
        retrieved_value = await cache_layer_instance.get_inference(key)
        assert retrieved_value == value

    async def test_cache_ttl_expiry(self, cache_layer_instance: CacheLayer):
        """C34: TTL=0.1 ثانیه، بعد از sleep(0.2)، assert None برگردد."""
        key = "expiring_key"
        value = {"data": "will_expire"}
        # Override ttl for this specific test to be shorter than default fixture
        cache_layer_instance._inference_cache.ttl = 0.1
        await cache_layer_instance.set_inference(key, value)

        # Wait longer than TTL
        await asyncio.sleep(0.2)

        retrieved_value = await cache_layer_instance.get_inference(key)
        assert retrieved_value is None

    async def test_cache_miss_returns_none(self, cache_layer_instance: CacheLayer):
        """C35: key ناموجود، assert None."""
        key = "non_existent_key"
        retrieved_value = await cache_layer_instance.get_inference(key)
        assert retrieved_value is None

    async def test_cache_invalidation(self, cache_layer_instance: CacheLayer):
        """C36: مقدار set، clear_all() فراخوانده شود، assert دیگر موجود نیست."""
        key1 = "key_to_invalidate_1"
        value1 = {"data": "value1"}
        key2 = "key_to_invalidate_2"
        value2 = {"data": "value2"}

        await cache_layer_instance.set_inference(key1, value1)
        await cache_layer_instance.set_token_count(key2, value2)

        assert await cache_layer_instance.get_inference(key1) == value1
        assert await cache_layer_instance.get_token_count(key2) == value2

        await cache_layer_instance.clear_all()

        assert await cache_layer_instance.get_inference(key1) is None
        assert await cache_layer_instance.get_token_count(key2) is None

    async def test_cache_key_collision_overwrite(self, cache_layer_instance: CacheLayer):
        """C37: یک key دو بار set با مقادیر مختلف، assert مقدار جدید."""
        key = "collision_key"
        old_value = {"data": "old"}
        new_value = {"data": "new"}

        await cache_layer_instance.set_inference(key, old_value)
        assert await cache_layer_instance.get_inference(key) == old_value

        await cache_layer_instance.set_inference(key, new_value)
        retrieved_value = await cache_layer_instance.get_inference(key)
        assert retrieved_value == new_value



