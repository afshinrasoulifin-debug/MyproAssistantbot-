
"""
tests/conftest.py — Shared pytest fixtures for ARKI Engine
════════════════════════════════════════════════════════════
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock

import pytest

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_env(monkeypatch):
    """Set standard test environment variables."""
    env_vars = {
        "BOT_TOKEN": "test-bot-token-123",
        "GEMINI_API_KEY": "test-gemini-key",
        "GROQ_API_KEY": "test-groq-key",
        "OPENROUTER_API_KEY": "test-openrouter-key",
        "KMS_MASTER_SECRET": "test-kms-secret-that-is-long-enough-for-testing-purposes",
        "ENCRYPTION_KEY": "test-encryption-key-for-testing-purposes-only",
        "ADMIN_IDS": "12345,67890",
        "DATABASE_URL": "sqlite+aiosqlite:///test_arki.db",
        "LOG_LEVEL": "DEBUG",
    }
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)
    return env_vars


@pytest.fixture
def mock_http_response():
    """Create a mock HTTP response factory."""
    def factory(status=200, json_data=None, text="", headers=None):
        resp = AsyncMock()
        resp.status = status
        resp.status_code = status
        resp.json = AsyncMock(return_value=json_data or {})
        resp.text = AsyncMock(return_value=text)
        resp.headers = headers or {}
        resp.read = AsyncMock(return_value=text.encode())
        return resp
    return factory


