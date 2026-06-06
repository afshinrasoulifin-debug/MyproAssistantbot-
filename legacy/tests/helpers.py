
"""
Test helpers for handler testing.
Provides mock Telegram objects and utilities.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock


class MockUser:
    """Mock Telegram User."""
    def __init__(self, user_id=12345, first_name="Test", username="testuser",
                 language_code="fa"):
        self.id = user_id
        self.first_name = first_name
        self.last_name = "User"
        self.username = username
        self.language_code = language_code
        self.is_bot = False
        self.full_name = f"{first_name} User"


class MockChat:
    """Mock Telegram Chat."""
    def __init__(self, chat_id=12345, chat_type="private"):
        self.id = chat_id
        self.type = chat_type
        self.title = "Test Chat"
        self.username = "testchat"


class MockMessage:
    """Mock Telegram Message."""
    def __init__(
        self,
        text: str = "/start",
        user_id: int = 12345,
        chat_id: int = 12345,
        message_id: int = 1,
    ):
        self.text = text
        self.message_id = message_id
        self.from_user = MockUser(user_id=user_id)
        self.chat = MockChat(chat_id=chat_id)
        self.date = None
        self.reply_to_message = None
        self.document = None
        self.photo = None
        self.voice = None
        self.video = None
        self.sticker = None

        # Mock async methods
        self.answer = AsyncMock(return_value=MagicMock(message_id=2))
        self.reply = AsyncMock(return_value=MagicMock(message_id=2))
        self.edit_text = AsyncMock()
        self.delete = AsyncMock()
        self.answer_photo = AsyncMock()
        self.answer_document = AsyncMock()


class MockCallbackQuery:
    """Mock Telegram CallbackQuery."""
    def __init__(self, data: str = "test", user_id: int = 12345):
        self.data = data
        self.from_user = MockUser(user_id=user_id)
        self.message = MockMessage(user_id=user_id)
        self.answer = AsyncMock()
        self.id = "callback_123"


class MockState:
    """Mock FSM State."""
    def __init__(self):
        self._data = {}

    async def get_data(self):
        return self._data

    async def set_data(self, data):
        self._data = data

    async def update_data(self, **kwargs):
        self._data.update(kwargs)

    async def set_state(self, state=None):
        self._state = state

    async def get_state(self):
        return getattr(self, '_state', None)

    async def clear(self):
        self._data = {}
        self._state = None


def run_async(coro):
    """Run async function in tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


