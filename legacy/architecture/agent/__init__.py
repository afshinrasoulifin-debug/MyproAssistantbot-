
"""architecture.agent — Autonomous agents for various bot subsystems"""
from .base import BaseAgent, AgentState
from .runtime_agent import RuntimeAgent, SyncAgent, UpdateAgent
from .automation_agent import AutomationAgent, MaintenanceAgent
from .support import SupportAgent, IntegrationAgent
from .deployment import DeploymentAgent, EndpointAgent, HostAgent, BridgeAgent

# ── Marketing TITAN Agent ──
try:
    from .marketing_agent import MarketingMasterAgent
except ImportError:
    MarketingMasterAgent = None  # Marketing TITAN module not installed

__all__ = ["AutomationAgent", "MaintenanceAgent", "AgentState", "AgentMetrics", "BaseAgent", "DeploymentAgent", "EndpointAgent", "HostAgent", "BridgeAgent", "RuntimeAgent", "SyncAgent", "UpdateAgent", "SupportAgent", "IntegrationAgent", "MarketingMasterAgent"]


