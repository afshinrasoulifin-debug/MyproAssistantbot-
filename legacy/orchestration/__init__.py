
from __future__ import annotations
"""
tg_bot/orchestration/ — Unified AI Orchestration Layer v17.0.0 (ABSTRACT-COGNITION)
══════════════════════════════════════════════════════════════════════════
Micro-Kernel architecture for multi-provider AI orchestration.

Core Modules (v10.3):
    1. ArkiOrchestrationController — Central lifecycle manager
    2. SmartRouter                 — Real-time optimal path selection
    3. SessionRepository           — Distributed session sync (Redis)
    4. OrchestrationMesh           — Stealth & Shaping execution
    5. ReplayBuffer                — Error recovery & Provider switching
"""

__version__ = "27.0.0"
__all__ = [
    "get_orchestrator",
    "boot_orchestrator",
    "Orchestrator",
    "ArkiOrchestrationController",
    "SmartRouter",
    "SessionRepository",
    "OrchestrationMesh",
    "ReplayBuffer",
]

_orchestrator_instance = None

def get_orchestrator() -> "Orchestrator":
    """Get the singleton orchestrator (created at boot)."""
    if _orchestrator_instance is None:
        # For backward compatibility, we'll auto-boot if not already booted
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # This is tricky in async, usually boot_orchestrator should be called in main.py
                pass
        except Exception:
            pass
        
    return _orchestrator_instance

async def boot_orchestrator(config: dict | None = None) -> "Orchestrator":
    """Boot the orchestration layer."""
    global _orchestrator_instance
    from .core import Orchestrator
    _orchestrator_instance = Orchestrator(config or {})
    await _orchestrator_instance.boot()
    return _orchestrator_instance

# ── v10.3 TITANIUM: Integration ──
from .controller import ArkiOrchestrationController
from .smart_router import SmartRouter
from .session_repository import SessionRepository
from .mesh import OrchestrationMesh
from .replay_buffer import ReplayBuffer
from .core import Orchestrator


