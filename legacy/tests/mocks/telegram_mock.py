
"""
Mock Telegram Bot API for testing.
"""
from unittest.mock import AsyncMock, MagicMock


class MockBot:
    """Mock Telegram Bot."""

    def __init__(self):
        self.send_message = AsyncMock(return_value=MagicMock(message_id=1))
        self.edit_message_text = AsyncMock()
        self.delete_message = AsyncMock()
        self.get_file = AsyncMock(return_value=MagicMock(file_path="test.txt"))
        self.download_file = AsyncMock(return_value=b"test content")
        self.answer_callback_query = AsyncMock()
        self.send_document = AsyncMock()
        self.send_photo = AsyncMock()
        self.send_voice = AsyncMock()
        self.get_me = AsyncMock(return_value=MagicMock(
            id=9999999, is_bot=True, username="arki_test_bot"
        ))
        self.set_my_commands = AsyncMock()
        self._sent_messages = []

    async def track_send(self, *args, **kwargs):
        self._sent_messages.append(kwargs)
        return MagicMock(message_id=len(self._sent_messages))


class MockAIClient:
    """Mock AI API client."""

    def __init__(self, default_response: str = "AI test response"):
        self._default = default_response
        self._calls = []

    async def generate(self, prompt: str, **kwargs) -> str:
        self._calls.append({"prompt": prompt, **kwargs})
        return self._default

    async def chat(self, messages: list, **kwargs) -> str:
        self._calls.append({"messages": messages, **kwargs})
        return self._default


class MockRedis:
    """Mock Redis client."""

    def __init__(self):
        self._store = {}

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value, ex=None):
        self._store[key] = value

    async def delete(self, key):
        self._store.pop(key, None)

    async def exists(self, key):
        return key in self._store


