
from __future__ import annotations
"""
architecture.adapter.platform — PlatformAdapter, RemoteAdapter, RuntimeAdapter
═══════════════════════════════════════════════════════════════════════════════
Adapters for different platforms (Telegram, web, API).
Covers: platform-adapter, remote-adapter, runtime-adapter
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional



logger = logging.getLogger(__name__)

class PlatformAdapter(ABC):
    """Abstract adapter for platform-specific operations."""
    def __init__(self, platform: str) -> None:
        self.platform = platform
        self._config: Dict[str, Any] = {}

    @abstractmethod
    async def send_message(self, target: Any, content: str) -> bool:
        raise NotImplementedError('Subclass must implement send_message')

    @abstractmethod
    async def receive_message(self) -> Optional[Dict[str, Any]]:
        raise NotImplementedError('Subclass must implement receive_message')

    def configure(self, **kwargs) -> None:
        self._config.update(kwargs)

class TelegramAdapter(PlatformAdapter):
    """Telegram-specific platform adapter."""
    def __init__(self) -> None:
        super().__init__("telegram")

    async def send_message(self, chat_id: Any, content: str) -> bool:
        logger.debug("TelegramAdapter.send_message(%s)", chat_id)
        return True

    async def receive_message(self) -> Optional[Dict[str, Any]]:
        return None

class RemoteAdapter(PlatformAdapter):
    """Adapter for remote API communication."""
    def __init__(self, base_url: str = "") -> None:
        super().__init__("remote")
        self.base_url = base_url

    async def send_message(self, endpoint: Any, content: str) -> bool:
        return True

    async def receive_message(self) -> Optional[Dict[str, Any]]:
        return None

class RuntimeAdapter(PlatformAdapter):
    """Adapter for internal runtime communication."""
    def __init__(self) -> None:
        super().__init__("runtime")

    async def send_message(self, target: Any, content: str) -> bool:
        return True

    async def receive_message(self) -> Optional[Dict[str, Any]]:
        return None


