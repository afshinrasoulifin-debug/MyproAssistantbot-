

import pytest
from unittest.mock import AsyncMock, patch

from arki_project.orchestration.retry_manager import RetryManager, RetryConfig
# Using base Exception classes as the specific ones are not in orchestration.types
class RateLimitError(Exception): pass
class OverloadedError(Exception): pass
class ConnectionError(Exception): pass
class TimeoutError(Exception): pass

@pytest.mark.asyncio
class TestOrchestrationRetryManager:

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        # Mock asyncio.sleep to prevent actual delays during tests
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            self.mock_sleep = mock_sleep
            yield

    async def test_retry_manager_success_first_try(self):
        """C15: callable موفق، assert فقط یک بار فراخوانده شود."""
        mock_callable = AsyncMock(return_value="Success")
        config = RetryConfig(max_retries=3, base_delay=0.1)
        retry_manager = RetryManager(config)

        result = await retry_manager.execute_with_retry(mock_callable)

        assert result == "Success"
        mock_callable.assert_called_once()
        self.mock_sleep.assert_not_called()

    async def test_retry_manager_exponential_backoff(self):
        """C16: با mock asyncio.sleep، assert delays بین retry‌ها نمایی باشند."""
        # Simulate failure twice, then success
        mock_callable = AsyncMock(side_effect=[RateLimitError("Too fast"), ConnectionError("No connection"), "Success"])
        config = RetryConfig(max_retries=2, base_delay=0.1, jitter_factor=0.0)
        retry_manager = RetryManager(config)

        result = await retry_manager.execute_with_retry(mock_callable)

        assert result == "Success"
        assert mock_callable.call_count == 3  # 1 initial attempt + 2 retries
        assert self.mock_sleep.call_count == 2

        # Expected delays: base_delay, base_delay * 2
        # With jitter_factor=0.0, delays should be exact
        assert self.mock_sleep.call_args_list[0].args[0] == pytest.approx(0.1)
        assert self.mock_sleep.call_args_list[1].args[0] == pytest.approx(0.2)

    async def test_retry_manager_max_attempts_respected(self):
        """C17: callable همیشه fail، assert دقیقاً max_attempts بار تلاش شود."""
        mock_callable = AsyncMock(side_effect=RateLimitError("Always fail"))
        config = RetryConfig(max_retries=2, base_delay=0.1)
        retry_manager = RetryManager(config)

        with pytest.raises(RateLimitError):
            await retry_manager.execute_with_retry(mock_callable)

        assert mock_callable.call_count == config.max_retries + 1 # 1 initial + max_retries
        assert self.mock_sleep.call_count == config.max_retries

    async def test_retry_manager_non_retryable_error(self):
        """C18: خطای ValueError که non-retryable است، assert فوری raise شود."""
        mock_callable = AsyncMock(side_effect=ValueError("Non-retryable error"))
        config = RetryConfig(max_retries=3, base_delay=0.1)
        retry_manager = RetryManager(config)

        with pytest.raises(ValueError, match="Non-retryable error"):
            await retry_manager.execute_with_retry(mock_callable)

        mock_callable.assert_called_once()
        self.mock_sleep.assert_not_called()

    async def test_retry_manager_config_backoff_multiplier(self):
        """C19: RetryConfig با multiplier=3، assert فاصله‌های صحیح."""
        mock_callable = AsyncMock(side_effect=[RateLimitError("1"), RateLimitError("2"), RateLimitError("3"), "Success"])
        # The RetryConfig in the source code does not have a 'multiplier' parameter.
        # It uses base_delay and doubles it implicitly (or uses jitter).
        # I will test the exponential growth based on base_delay * (2^retry_num).
        # The user's request for 'multiplier=3' implies a custom multiplier, which is not directly supported.
        # I will implement this test based on the default exponential backoff (multiplier of 2).
        # If a custom multiplier is desired, the RetryConfig class needs modification.

        config = RetryConfig(max_retries=3, base_delay=0.1, jitter_factor=0.0)
        retry_manager = RetryManager(config)

        await retry_manager.execute_with_retry(mock_callable)

        assert mock_callable.call_count == 4 # 1 initial + 3 retries
        assert self.mock_sleep.call_count == 3

        # Expected delays: base_delay, base_delay * 2, base_delay * 4
        assert self.mock_sleep.call_args_list[0].args[0] == pytest.approx(0.1)
        assert self.mock_sleep.call_args_list[1].args[0] == pytest.approx(0.2)
        assert self.mock_sleep.call_args_list[2].args[0] == pytest.approx(0.4)

        # Note: The original request mentioned 'multiplier=3'. The current RetryConfig
        # implementation uses a fixed multiplier of 2 for exponential backoff.
        # To support a custom multiplier, the RetryConfig and _backoff_delay function
        # would need to be updated. This test reflects the current code's behavior.


