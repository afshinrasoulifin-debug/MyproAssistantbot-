
"""architecture.adapter — Platform, integration, and transport adapters"""
from .platform import PlatformAdapter, RemoteAdapter, RuntimeAdapter
from .integration import IntegrationAdapter, CompatibilityAdapter
from .transport import TransportAdapter, SystemAdapter

__all__ = ["IntegrationAdapter", "CompatibilityAdapter", "PlatformAdapter", "TelegramAdapter", "RemoteAdapter", "RuntimeAdapter", "TransportAdapter", "InMemoryTransport", "SystemAdapter"]


