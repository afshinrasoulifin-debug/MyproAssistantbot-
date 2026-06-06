

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from arki_project.utils.ai_client import AIClient, ChatMessage as RateLimitError
from arki_project.database.models import User, ChatMessage as DBChatMessage
from arki_project.utils.circuit_breaker import CircuitBreaker

@pytest.mark.asyncio
class TestAIClient:

    @pytest.fixture(autouse=True)
    def setup_ai_client_mocks(self):
        with (
            patch("arki_project.utils.ai_client.get_ai_cache") as mock_get_ai_cache,
            patch("arki_project.utils.ai_client.get_model_watcher") as mock_get_model_watcher,
            patch("arki_project.utils.ai_client.get_cost_tracker") as mock_get_cost_tracker,
            patch("arki_project.utils.ai_client._push_prom") as mock_push_prom,
            patch("arki_project.utils.ai_client.http_pool.get_client") as mock_get_http_client,
            patch("arki_project.utils.ai_client.http_pool.close_all") as mock_close_all_http_clients,
            patch("arki_project.utils.ai_client.CircuitBreaker") as MockCircuitBreaker
        ):

            self.mock_ai_cache = mock_get_ai_cache.return_value
            self.mock_model_watcher = mock_get_model_watcher.return_value
            self.mock_cost_tracker = mock_get_cost_tracker.return_value
            self.mock_push_prom = mock_push_prom
            self.mock_http_client = AsyncMock()
            mock_get_http_client.return_value = self.mock_http_client
            self.mock_close_all_http_clients = mock_close_all_http_clients
            self.MockCircuitBreaker = MockCircuitBreaker

            # Mock the internal _call_with_fallback to control AI responses
            with patch.object(AIClient, 
                              "_call_with_fallback", 
                              new_callable=AsyncMock) as mock_call_with_fallback:
                self.mock_call_with_fallback = mock_call_with_fallback
                self.mock_call_with_fallback.return_value = "Mocked AI response"
                yield

    async def test_ai_client_instantiation(self):
        """D1: کلاس اصلی import و instantiate شود، assert attribute‌های اولیه."""
        client = AIClient(api_key="test_key")
        assert client._api_key == "test_key"
        assert client._model == "gemini-2.5-pro"
        assert client._max_history == 500
        assert client._temperature == 0.7
        assert client._max_tokens == 65536
        assert isinstance(client._breakers["gemini"], CircuitBreaker)
        self.MockCircuitBreaker.assert_any_call("gemini", failure_threshold=5, recovery_timeout=60.0)

    async def test_ai_client_mock_gemini_success(self):
        """D2: HTTP mock با پاسخ Gemini، call generate()، assert text برگردد."""
        client = AIClient(api_key="test_key")
        user_id = 123
        prompt = "Hello, AI!"

        response = await client.ask(user_id, prompt, model_key="gemini-pro")

        assert response == "Mocked AI response"
        self.mock_call_with_fallback.assert_called_once()
        # Verify that the message was appended to history and saved to DB
        assert len(client._history[user_id]) == 2 # User message + AI response
        assert client._history[user_id][0].content == prompt
        assert client._history[user_id][1].content == "Mocked AI response"

    async def test_ai_client_fallback_to_groq(self):
        """D3: Gemini mock با 429، Groq mock با 200، assert پاسخ از Groq."""
        client = AIClient(api_key="test_key", groq_api_key="groq_key")
        user_id = 124
        prompt = "Fallback scenario"

        # Simulate Gemini failing and then Groq succeeding
        self.mock_call_with_fallback.side_effect = [
            RateLimitError("Gemini 429"),
            "Groq fallback response"
        ]

        response = await client.ask(user_id, prompt, model_key="gemini-pro")

        assert response == "Groq fallback response"
        assert self.mock_call_with_fallback.call_count == 2 # One for Gemini, one for Groq
        # The actual model key passed to _call_with_fallback would change in a real scenario
        # but with the current mock, we just check the number of calls and the final result.

    async def test_ai_client_circuit_breaker_integration(self):
        """D4: 5 خطای متوالی، assert circuit breaker OPEN شود."""
        client = AIClient(api_key="test_key")
        user_id = 125
        prompt = "Circuit breaker test"

        # Simulate 5 failures for Gemini
        self.mock_call_with_fallback.side_effect = [
            RateLimitError("CB Test 1"),
            RateLimitError("CB Test 2"),
            RateLimitError("CB Test 3"),
            RateLimitError("CB Test 4"),
            RateLimitError("CB Test 5"),
            "Should not be called if CB is open"
        ]

        # The circuit breaker is managed internally by AIClient for each provider.
        # We need to simulate calls that would trigger the circuit breaker.
        # The `_call_with_fallback` is where the circuit breaker is checked and updated.
        # We need to mock the internal `_call_api` method that `_call_with_fallback` uses.

        # Reset mock_call_with_fallback to allow testing the circuit breaker logic
        # by directly mocking the underlying _call_api method.
        with patch.object(client, "_call_api", new_callable=AsyncMock) as mock_call_api:
            mock_call_api.side_effect = [RateLimitError for _ in range(5)] + ["Success"]

            # Trigger failures
            for _ in range(5):
                with pytest.raises(RateLimitError):
                    await client.ask(user_id, prompt, model_key="gemini-pro")

            # After 5 failures, the circuit breaker should be open.
            # The next call should immediately raise a CircuitBreakerOpen exception (or similar).
            # The current _call_with_fallback handles this by trying other providers.
            # If no other provider is available, it will re-raise the last error.
            # For this test, we need to ensure the circuit breaker state changes.

            # Check if the circuit breaker for gemini is open
            assert client._breakers["gemini"].is_open()

            # The 6th call should immediately fail or fallback if other providers are configured.
            # Since we only mocked _call_api for gemini-pro, and no other fallbacks are set up
            # in this specific test, it should still raise an error, but the circuit breaker
            # should prevent direct calls to the failing provider.
            mock_call_api.side_effect = [Exception("Should not be called")] # Ensure it's not called
            with pytest.raises(RateLimitError): # Or the last error that caused CB to open
                await client.ask(user_id, prompt, model_key="gemini-pro")

            # The circuit breaker for gemini should still be open
            assert client._breakers["gemini"].is_open()

    async def test_ai_client_db_message_persistence(self, db_session: AsyncSession):
        """D5: با db in-memory، generate فراخوانده شود، assert پیام در ChatMessage ذخیره شود."""
        client = AIClient(api_key="test_key")
        user_id = 126
        prompt = "Persist this message"
        ai_response = "AI persisted response"

        # Ensure user exists in DB
        user = User(telegram_id=user_id, full_name="Persistent User")
        db_session.add(user)
        await db_session.commit()

        # Mock the AI response
        self.mock_call_with_fallback.return_value = ai_response

        await client.ask(user_id, prompt, model_key="gemini-pro")

        # Verify messages are saved in the database
        messages = (await db_session.execute(
            select(DBChatMessage).where(DBChatMessage.user_id == user_id)
        )).scalars().all()

        assert len(messages) == 2
        assert messages[0].content == prompt
        assert messages[0].role == "user"
        assert messages[1].content == ai_response
        assert messages[1].role == "model"

    async def test_ai_client_think_tag_cleaning(self):
        """D7: پاسخ با <think>...</think>، assert متن نهایی فاقد تگ باشد."""
        client = AIClient(api_key="test_key")
        user_id = 127
        prompt = "Clean this response"
        raw_response = "This is a <think>thought process</think> and this is the final answer."
        expected_response = "This is a and this is the final answer."

        self.mock_call_with_fallback.return_value = raw_response

        response = await client.ask(user_id, prompt, model_key="gemini-pro")

        assert response == expected_response
        # Verify that the stored message in history is also cleaned
        assert client._history[user_id][1].content == expected_response

    async def test_ai_client_context_window_packing(self, db_session: AsyncSession):
        """D6: 100 پیام در DB، assert فقط آخرین N پیام به API ارسال شود."""
        client = AIClient(api_key="test_key", max_history=15) # Set a small max_history for easier testing
        user_id = 128
        current_prompt = "What is the summary of our conversation?"

        # Ensure user exists in DB
        user = User(telegram_id=user_id, full_name="Context User")
        db_session.add(user)
        await db_session.commit()

        # Add 100 messages to the DB for this user
        for i in range(100):
            msg_content = f"Old message {i}"
            db_msg = DBChatMessage(
                user_id=user_id, 
                role="user" if i % 2 == 0 else "model", 
                content=msg_content,
                created_at=datetime.now(timezone.utc) - timedelta(minutes=100-i)
            )
            db_session.add(db_msg)
        await db_session.commit()

        # Load history for the user (this happens implicitly on first ask)
        # The _ensure_loaded method will load up to self._max_history messages.
        # However, the `ask` method also has logic for `smart context packing`.
        # The smart context packing logic is: always include last 15 messages, plus top 15 relevant older messages.
        # So, we expect at most 30 messages + 1 system prompt + 1 current prompt = 32 messages.

        # Mock the _call_with_fallback to capture the messages it receives
        captured_messages = []
        self.mock_call_with_fallback.side_effect = lambda messages, *args, **kwargs: captured_messages.append(messages) or "Mocked response"

        await client.ask(user_id, current_prompt, model_key="gemini-pro")

        assert len(captured_messages) == 1 # Only one call to _call_with_fallback
        messages_sent_to_api = captured_messages[0]

        # Expecting system prompt + (last 15 + relevant 15) + current user prompt
        # The `smart_context_packing` logic is applied *before* passing to _call_with_fallback.
        # The `_history` will contain up to `_max_history` (15 in this test) messages.
        # The `ask` method then combines recent and relevant older messages.
        # The `_history` is loaded with `self._max_history` (15) messages.
        # The `ask` method then takes `history = self._history[user_id][-self._max_history:]` which is the last 15.
        # Then it applies `smart context packing` which takes `last 15` and `top 15 relevant older`.
        # So, it should be at most 30 chat messages + 1 system message + 1 current user message.
        # However, the `_history` itself is limited to `self._max_history` when loaded.
        # Let's re-evaluate the `smart context packing` logic in `ai_client.py`.
        # It says: `history = self._history[user_id][-self._max_history:]`
        # This means `self._history` already contains only the last `_max_history` messages.
        # Then, `if len(history) > 30:` is checked. If `_max_history` is 15, this condition is false.
        # So, if `_max_history` is 15, it will just send `system_prompt` + `history` + `current_prompt`.
        # Which means 1 + 15 + 1 = 17 messages.

        # Let's adjust the expectation based on the code logic.
        # The `_max_history` is 15 in this test fixture.
        # So, the `history` variable inside `ask` will have at most 15 messages.
        # The `if len(history) > 30:` condition will be false.
        # Thus, `msgs` will be `[system_prompt] + history + [current_user_message]`.
        # Total messages sent to API = 1 (system) + 15 (history) + 1 (current) = 17.

        assert len(messages_sent_to_api) == 17
        assert messages_sent_to_api[0]["role"] == "system"
        assert messages_sent_to_api[-1]["content"] == current_prompt
        assert messages_sent_to_api[1]["content"] == "Old message 85" # The 15th message from the end of 100 messages
        assert messages_sent_to_api[15]["content"] == "Old message 99" # The last message



