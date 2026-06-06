
"""Test architecture.core"""
from core.architecture.core.runtime import RuntimeCore, get_runtime
from core.architecture.core.config import AdvancedConfig, FeatureFlags
from core.architecture.core.hooks import RuntimeHooks

class TestRuntimeCore:
    def test_singleton(self):
        r1 = get_runtime()
        r2 = get_runtime()
        assert r1 is r2

    def test_phase(self):
        runtime = RuntimeCore()
        assert runtime.phase is not None
        assert runtime.phase is not None

    def test_stats(self):
        runtime = RuntimeCore()
        assert isinstance(runtime.stats, dict)

class TestAdvancedConfig:
    def test_define_and_get(self):
        config = AdvancedConfig()
        config.define("test.key", "value123")
        assert config.get("test.key") == "value123"

    def test_default_value(self):
        config = AdvancedConfig()
        assert config.get("nonexistent", "default") == "default"

    def test_override(self):
        config = AdvancedConfig()
        config.define("key", "v1")
        config.define("key", "v2")
        assert config.get("key") == "v2"

class TestFeatureFlags:
    def test_register_and_check(self):
        flags = FeatureFlags()
        flags.register("my_feature", enabled=True, description="Test flag")
        assert flags.is_enabled("my_feature") is True

    def test_disabled_flag(self):
        flags = FeatureFlags()
        flags.register("disabled", enabled=False)
        assert flags.is_enabled("disabled") is False

    def test_unknown_flag(self):
        flags = FeatureFlags()
        assert flags.is_enabled("nonexistent") is False

    def test_toggle(self):
        flags = FeatureFlags()
        flags.register("toggle_me", enabled=False)
        flags.toggle("toggle_me", enabled=True)
        assert flags.is_enabled("toggle_me") is True

class TestRuntimeHooks:
    def test_register(self):
        hooks = RuntimeHooks()
        hooks.register("before_start", lambda ctx: None)
        assert len(hooks.list_hooks()) >= 1

    def test_trigger_no_error(self):
        hooks = RuntimeHooks()
        hooks.trigger("nonexistent", {})  # Should not raise


