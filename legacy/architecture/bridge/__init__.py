
"""architecture.bridge — System bridges for cross-subsystem communication"""
from .core import BridgeCore, SystemBridge, NativeBridge
from .process import ProcessBridge, IPCBridge
from .transport_bridge import TransportBridge, StorageBridge
from .data import DataBridge

__all__ = ["BridgeCore", "SystemBridge", "NativeBridge", "DataBridge", "ProcessBridge", "IPCBridge", "TransportBridge", "StorageBridge"]


