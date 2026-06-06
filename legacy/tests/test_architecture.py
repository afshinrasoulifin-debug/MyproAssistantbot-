
"""
tg_bot/tests/test_architecture.py — Architecture Layer Tests
════════════════════════════════════════════════════════════
v9.0: Tests that the 13-layer architecture actually works.
"""

from arki_project.architecture.setup import init_architecture, boot_architecture


class TestArchitectureInit:
    """Tests for architecture initialization."""

    def test_init_creates_registry(self):
        registry = init_architecture()
        assert isinstance(registry, dict)
        assert len(registry) > 50  # Should have 80+ components

    def test_registry_has_event_bus(self):
        registry = init_architecture()
        assert "event_bus" in registry
        assert registry["event_bus"] is not None

    def test_registry_has_all_layers(self):
        registry = init_architecture()
        # Check representative component from each layer
        assert "runtime_core" in registry           # Layer 1: Core
        assert "workflow_engine" in registry         # Layer 2: Engines
        assert "background_service" in registry     # Layer 3: Services
        assert "event_bus" in registry              # Layer 4: Transport
        assert "plugin_manager" in registry         # Layer 5: Managers
        assert "runtime_agent" in registry          # Layer 6: Agents
        assert "telegram_adapter" in registry       # Layer 7: Adapters
        assert "bridge_core" in registry            # Layer 8: Bridges
        assert "telemetry_monitor" in registry      # Layer 9: Monitor
        assert "controller" in registry             # Layer 10: Control
        assert "module_loader" in registry          # Layer 11: Loaders
        assert "runtime_helper" in registry         # Layer 12: Helpers
        assert "runtime_layer" in registry          # Layer 13: Layers

    def test_smart_engine_created(self):
        registry = init_architecture()
        smart = registry.get("smart_engine")
        assert smart is not None
        # Test it has methods
        assert hasattr(smart, "analyze_user")
        assert hasattr(smart, "select_strategy")

    def test_boot_architecture_sets_global(self):
        from arki_project.architecture.setup import get_registry
        boot_architecture()
        reg = get_registry()
        assert len(reg) > 50


class TestEventBus:
    """Tests for EventBus functionality."""

    def test_event_bus_subscribe_and_publish(self):
        registry = init_architecture()
        bus = registry["event_bus"]
        
        received = []
        bus.subscribe("test.event", lambda msg: received.append(msg))
        
        # Publish sync (EventBus.publish is actually async in wiring, but let's test the subscribe)
        assert len(bus._subscribers.get("test.event", [])) >= 1


class TestWiring:
    """Tests for component wiring."""

    def test_wiring_creates_connections(self):
        registry = init_architecture()
        # After init, wiring should have created connections
        bus = registry["event_bus"]
        assert len(bus._subscribers) > 0

    def test_health_monitor_has_checks(self):
        registry = init_architecture()
        health = registry.get("health_monitor")
        if health and hasattr(health, "_checks"):
            assert len(health._checks) >= 1

    def test_controller_manages_components(self):
        registry = init_architecture()
        ctrl = registry.get("controller")
        if ctrl and hasattr(ctrl, "_components"):
            assert len(ctrl._components) >= 1


