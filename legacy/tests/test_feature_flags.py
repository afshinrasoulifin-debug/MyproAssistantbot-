
"""Tests for feature flag system."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFeatureFlags:
    def test_default_flags_enabled(self):
        from arki_project.utils.feature_flags import FeatureFlagManager
        ff = FeatureFlagManager(config_path="/tmp/test_flags.json")
        assert ff.is_enabled("ai_chat") is True
        assert ff.is_enabled("web_search") is True

    def test_toggle(self):
        from arki_project.utils.feature_flags import FeatureFlagManager
        ff = FeatureFlagManager(config_path="/tmp/test_flags2.json")
        result = ff.toggle("ai_chat")
        assert result is False
        result2 = ff.toggle("ai_chat")
        assert result2 is True

    def test_disable_enable(self):
        """v9.7.1: All features always enabled (unlocked)."""
        from arki_project.utils.feature_flags import FeatureFlagManager
        ff = FeatureFlagManager(config_path="/tmp/test_flags3.json")
        ff.disable("billing")
        assert ff.is_enabled("billing") is True  # v9.7.1: Always True
        ff.enable("billing")
        assert ff.is_enabled("billing") is True

    def test_unknown_flag_defaults_true(self):
        from arki_project.utils.feature_flags import FeatureFlagManager
        ff = FeatureFlagManager(config_path="/tmp/test_flags4.json")
        assert ff.is_enabled("nonexistent_feature") is True

    def test_list_all(self):
        from arki_project.utils.feature_flags import FeatureFlagManager
        ff = FeatureFlagManager(config_path="/tmp/test_flags5.json")
        all_flags = ff.list_all()
        assert isinstance(all_flags, dict)
        assert len(all_flags) > 10


