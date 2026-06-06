
"""
Arki v8 Enterprise Architecture Layer
═══════════════════════════════════════
13 packages · 50+ modules · 250+ components

Layered architecture for doctoral-grade AI Telegram bot:

    Layer 1 — Core:       runtime, bootstrap, config, hooks
    Layer 2 — Engine:     workflow, automation, orchestration, execution, processing, template, smart
    Layer 3 — Service:    background, sync, update, maintenance, remote
    Layer 4 — Transport:  bus, router, dispatcher, channel
    Layer 5 — Manager:    plugin, task, session, deployment
    Layer 6 — Agent:      runtime, automation, support, deployment
    Layer 7 — Adapter:    platform, integration, transport
    Layer 8 — Bridge:     core, process, transport, data
    Layer 9 — Monitor:    telemetry, health, console
    Layer 10 — Control:   controller, plane
    Layer 11 — Loader:    module, plugin, bootstrap
    Layer 12 — Helper:    runtime, integration, support, command
    Layer 13 — Layer:     runtime, execution, orchestration, control
"""

try:
    from config import APP_VERSION as __version__
except ImportError:
    __version__ = "29.0.0"
__all__ = [
    "core", "engine", "service", "transport", "manager",
    "agent", "adapter", "bridge", "monitor", "control",
    "loader", "helper", "layer",
]


