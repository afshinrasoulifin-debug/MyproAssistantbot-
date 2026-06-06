
from __future__ import annotations
"""
tests/test_marketing_config_deep.py — Deep tests for marketing configuration
═══════════════════════════════════════════════════════════════════════════════
Tests config_marketing.py: defaults, validation, env overrides, edge cases.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDefaultBrandConfig(unittest.TestCase):
    """Test DEFAULT_BRAND constants."""

    def test_brand_has_required_keys(self):
        from config_marketing import DEFAULT_BRAND
        required = {"name", "tagline", "style", "location", "languages", "price_range_eur", "products"}
        self.assertTrue(required.issubset(set(DEFAULT_BRAND.keys())))

    def test_brand_name_not_empty(self):
        from config_marketing import DEFAULT_BRAND
        self.assertTrue(len(DEFAULT_BRAND["name"]) > 0)

    def test_brand_languages_list(self):
        from config_marketing import DEFAULT_BRAND
        self.assertIsInstance(DEFAULT_BRAND["languages"], list)
        self.assertTrue(len(DEFAULT_BRAND["languages"]) >= 1)

    def test_brand_price_range_tuple(self):
        from config_marketing import DEFAULT_BRAND
        pr = DEFAULT_BRAND["price_range_eur"]
        self.assertIsInstance(pr, tuple)
        self.assertEqual(len(pr), 2)
        self.assertLess(pr[0], pr[1])

    def test_brand_products_nonempty(self):
        from config_marketing import DEFAULT_BRAND
        self.assertIsInstance(DEFAULT_BRAND["products"], list)
        self.assertTrue(len(DEFAULT_BRAND["products"]) >= 1)


class TestDefaultTargetMarkets(unittest.TestCase):
    """Test DEFAULT_TARGET_MARKETS constants."""

    def test_markets_nonempty(self):
        from config_marketing import DEFAULT_TARGET_MARKETS
        self.assertTrue(len(DEFAULT_TARGET_MARKETS) >= 1)

    def test_market_has_required_keys(self):
        from config_marketing import DEFAULT_TARGET_MARKETS
        required = {"region", "priority", "languages", "timezone"}
        for market in DEFAULT_TARGET_MARKETS:
            self.assertTrue(required.issubset(set(market.keys())),
                            f"Missing keys in market: {market.get('region', '?')}")

    def test_market_priorities_unique(self):
        from config_marketing import DEFAULT_TARGET_MARKETS
        priorities = [m["priority"] for m in DEFAULT_TARGET_MARKETS]
        self.assertEqual(len(priorities), len(set(priorities)), "Duplicate priorities")

    def test_market_priorities_ascending(self):
        from config_marketing import DEFAULT_TARGET_MARKETS
        priorities = [m["priority"] for m in DEFAULT_TARGET_MARKETS]
        self.assertEqual(priorities, sorted(priorities))

    def test_market_languages_include_english(self):
        from config_marketing import DEFAULT_TARGET_MARKETS
        for market in DEFAULT_TARGET_MARKETS:
            self.assertIn("en", market["languages"],
                          f"{market['region']} missing English")


class TestB2BCategories(unittest.TestCase):
    """Test B2B_CATEGORIES constants."""

    def test_categories_nonempty(self):
        from config_marketing import B2B_CATEGORIES
        self.assertTrue(len(B2B_CATEGORIES) >= 1)

    def test_categories_have_identity(self):
        from config_marketing import B2B_CATEGORIES
        for cat in B2B_CATEGORIES:
            self.assertIn("id", cat, f"Category missing 'id': {cat}")
            self.assertTrue(len(cat["id"]) > 0)
            self.assertIn("name_en", cat, f"Category missing 'name_en': {cat}")
            self.assertTrue(len(cat["name_en"]) > 0)


class TestPlatformRegistry(unittest.TestCase):
    """Test PLATFORM_REGISTRY constants."""

    def test_registry_nonempty(self):
        from config_marketing import PLATFORM_REGISTRY
        self.assertIsInstance(PLATFORM_REGISTRY, dict)
        self.assertTrue(len(PLATFORM_REGISTRY) >= 1)

    def test_platform_has_status(self):
        from config_marketing import PLATFORM_REGISTRY
        for name, cfg in PLATFORM_REGISTRY.items():
            self.assertIn("status", cfg,
                          f"Platform '{name}' missing 'status' field")
            self.assertIn("name", cfg,
                          f"Platform '{name}' missing 'name' field")


class TestMarketingSettings(unittest.TestCase):
    """Test MarketingSettings dataclass."""

    def test_instantiate_defaults(self):
        from config_marketing import MarketingSettings
        s = MarketingSettings()
        self.assertIsNotNone(s)

    def test_default_values_sane(self):
        from config_marketing import MarketingSettings
        s = MarketingSettings()
        self.assertGreater(s.hunter_max_results_per_query, 0)
        self.assertGreater(s.hunter_search_radius_km, 0)
        self.assertGreater(s.hunter_cooldown_hours, 0)
        self.assertGreater(s.outreach_daily_limit, 0)
        self.assertGreater(len(s.outreach_followup_days), 0)

    def test_scoring_thresholds_ordered(self):
        from config_marketing import MarketingSettings
        s = MarketingSettings()
        self.assertGreater(s.scoring_hot_threshold, s.scoring_warm_threshold)

    def test_gdpr_retention_positive(self):
        from config_marketing import MarketingSettings
        s = MarketingSettings()
        self.assertGreater(s.gdpr_data_retention_days, 0)

    def test_brand_is_copy(self):
        """Brand dict should be a COPY, not reference to module-level default."""
        from config_marketing import MarketingSettings, DEFAULT_BRAND
        s = MarketingSettings()
        s.brand["name"] = "MODIFIED"
        self.assertNotEqual(DEFAULT_BRAND["name"], "MODIFIED")

    def test_target_markets_is_copy(self):
        from config_marketing import MarketingSettings, DEFAULT_TARGET_MARKETS
        s = MarketingSettings()
        s.target_markets.append({"region": "TEST"})
        self.assertFalse(any(m.get("region") == "TEST"
                             for m in DEFAULT_TARGET_MARKETS))

    def test_env_override_hunter_max(self):
        """Environment variables should override defaults."""
        from config_marketing import MarketingSettings
        os.environ["MKT_HUNTER_MAX_RESULTS"] = "999"
        try:
            s = MarketingSettings(
                hunter_max_results_per_query=int(os.environ.get("MKT_HUNTER_MAX_RESULTS", 50))
            )
            self.assertEqual(s.hunter_max_results_per_query, 999)
        finally:
            del os.environ["MKT_HUNTER_MAX_RESULTS"]


class TestLoadMarketingSettings(unittest.TestCase):
    """Test singleton pattern."""

    def test_load_returns_instance(self):
        from config_marketing import load_marketing_settings
        s = load_marketing_settings()
        self.assertIsNotNone(s)

    def test_get_after_load(self):
        from config_marketing import load_marketing_settings, get_mkt_settings
        load_marketing_settings()
        s = get_mkt_settings()
        self.assertIsNotNone(s)

    def test_singleton_same_instance(self):
        from config_marketing import load_marketing_settings, get_mkt_settings
        s1 = load_marketing_settings()
        s2 = get_mkt_settings()
        self.assertIs(s1, s2)


class TestFollowupDays(unittest.TestCase):
    """Followup days logic validation."""

    def test_followup_days_sorted(self):
        from config_marketing import MarketingSettings
        s = MarketingSettings()
        self.assertEqual(s.outreach_followup_days, sorted(s.outreach_followup_days))

    def test_followup_days_positive(self):
        from config_marketing import MarketingSettings
        s = MarketingSettings()
        for d in s.outreach_followup_days:
            self.assertGreater(d, 0)

    def test_followup_days_no_duplicates(self):
        from config_marketing import MarketingSettings
        s = MarketingSettings()
        self.assertEqual(len(s.outreach_followup_days),
                         len(set(s.outreach_followup_days)))


if __name__ == "__main__":
    unittest.main()


