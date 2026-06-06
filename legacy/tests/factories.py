
from __future__ import annotations
import os
"""
Test data factories for creating test objects.
"""
import time
from unittest.mock import MagicMock, AsyncMock


class UserFactory:
    """Create mock User objects."""
    _counter = 0

    @classmethod
    def create(cls, user_id: int = None, username: str = None,
               first_name: str = "Test", is_admin: bool = False):
        cls._counter += 1
        user = MagicMock()
        user.id = user_id or (100000 + cls._counter)
        user.user_id = user.id
        user.username = username or f"testuser_{cls._counter}"
        user.first_name = first_name
        user.is_bot = False
        user.language_code = "fa"
        user.is_admin = is_admin
        return user


class MessageFactory:
    """Create mock Message objects."""
    _counter = 0

    @classmethod
    def create(cls, text: str = "/start", user=None, chat_id: int = None,
               document=None, photo=None, reply_to=None):
        cls._counter += 1
        msg = AsyncMock()
        msg.message_id = cls._counter
        msg.text = text
        msg.caption = None
        msg.from_user = user or UserFactory.create()
        msg.chat = MagicMock()
        msg.chat.id = chat_id or msg.from_user.id
        msg.chat.type = "private"
        msg.date = MagicMock()
        msg.document = document
        msg.photo = photo
        msg.reply_to_message = reply_to
        msg.reply = AsyncMock()
        msg.answer = AsyncMock()
        msg.answer_document = AsyncMock()
        msg.bot = AsyncMock()
        msg.bot.get_file = AsyncMock()
        msg.bot.download_file = AsyncMock()
        return msg


class CallbackFactory:
    """Create mock CallbackQuery objects."""

    @classmethod
    def create(cls, data: str = "test", user=None, message=None):
        cb = AsyncMock()
        cb.id = str(int(time.time()))
        cb.data = data
        cb.from_user = user or UserFactory.create()
        cb.message = message or MessageFactory.create()
        cb.answer = AsyncMock()
        return cb


class SettingsFactory:
    """Create mock Settings objects."""

    @classmethod
    def create(cls, bot_token: str = "test:token", ai_key: str = "test-key"):
        settings = MagicMock()
        settings.BOT_TOKEN = bot_token
        settings.AI_API_KEY = ai_key
        settings.AI_MODEL = "gemini-2.5-flash"
        settings.AI_MAX_TOKENS = 8192
        settings.AI_TEMPERATURE = 0.7
        settings.ADMIN_IDS = [int(os.environ.get('ADMIN_IDS', '123456789'))]
        settings.RATE_LIMIT_MESSAGES = 999
        settings.DEFAULT_LANGUAGE = "fa"
        return settings


class DBSessionFactory:
    """Create mock database session."""

    @classmethod
    def create(cls):
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        return session


