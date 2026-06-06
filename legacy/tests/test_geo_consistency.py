
"""Tests for utils/geo_consistency.py — Geographic Consistency Engine."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.geo_consistency import (
    GEO_DATABASE,
    GeoConsistencyEngine,
    GeoConsistencyValidator,
    IntlFingerprint,
    Region,
    US_TIMEZONES,
    CA_TIMEZONES,
    AU_TIMEZONES,
    geo_engine,
)


# ═══════════════════════════════════════════════════════════
# GEO_DATABASE Tests
# ═══════════════════════════════════════════════════════════

class TestGeoDatabase:
    def test_database_has_20_countries(self):
        assert len(GEO_DATABASE) == 20

    def test_finland_exists(self):
        assert "FI" in GEO_DATABASE
        fi = GEO_DATABASE["FI"]
        assert fi.country_name == "Finland"
        assert fi.primary_language == "fi"
        assert fi.timezone == "Europe/Helsinki"
        assert fi.currency == "EUR"

    def test_us_exists(self):
        us = GEO_DATABASE["US"]
        assert us.country_name == "United States"
        assert us.measurement == "imperial"
        assert us.currency == "USD"

    def test_iran_exists(self):
        ir = GEO_DATABASE["IR"]
        assert ir.writing_direction == "rtl"
        assert ir.primary_language == "fa"

    def test_all_locales_have_required_fields(self):
        for code, locale in GEO_DATABASE.items():
            assert locale.country_code == code
            assert locale.country_name, f"{code} missing country_name"
            assert locale.primary_language, f"{code} missing primary_language"
            assert locale.timezone, f"{code} missing timezone"
            assert locale.currency, f"{code} missing currency"
            assert locale.region is not None

    def test_all_locales_have_languages(self):
        for code, locale in GEO_DATABASE.items():
            assert len(locale.languages) >= 1, f"{code} has no languages"

    def test_accept_language_not_empty(self):
        for code, locale in GEO_DATABASE.items():
            assert locale.accept_language, f"{code} missing accept_language"

    def test_to_dict(self):
        fi = GEO_DATABASE["FI"]
        d = fi.to_dict()
        assert d["country_code"] == "FI"
        assert d["region"] == "nordic"
        assert "timezone" in d

    def test_regions_cover_all_types(self):
        regions = {locale.region for locale in GEO_DATABASE.values()}
        assert Region.EUROPE in regions
        assert Region.NORDIC in regions
        assert Region.NORTH_AMERICA in regions
        assert Region.ASIA_PACIFIC in regions
        assert Region.MIDDLE_EAST in regions


class TestMultiTimezones:
    def test_us_has_6_timezones(self):
        assert len(US_TIMEZONES) == 6

    def test_ca_has_5_timezones(self):
        assert len(CA_TIMEZONES) == 5

    def test_au_has_3_timezones(self):
        assert len(AU_TIMEZONES) == 3

    def test_timezone_tuples_have_correct_format(self):
        for name, (tz, offset) in US_TIMEZONES.items():
            assert isinstance(tz, str)
            assert isinstance(offset, int)


# ═══════════════════════════════════════════════════════════
# IntlFingerprint Tests
# ═══════════════════════════════════════════════════════════

class TestIntlFingerprint:
    def test_timezone_override_script(self):
        fi = GEO_DATABASE["FI"]
        script = IntlFingerprint.timezone_override_script(fi)
        assert "Europe/Helsinki" in script
        assert str(fi.timezone_offset) in script

    def test_date_format_script(self):
        fi = GEO_DATABASE["FI"]
        script = IntlFingerprint.date_format_script(fi)
        assert "'fi'" in script

    def test_number_format_script(self):
        us = GEO_DATABASE["US"]
        script = IntlFingerprint.number_format_script(us)
        assert "'en-US'" in script

    def test_currency_format_script(self):
        de = GEO_DATABASE["DE"]
        script = IntlFingerprint.currency_format_script(de)
        assert "'EUR'" in script

    def test_get_all_scripts(self):
        fi = GEO_DATABASE["FI"]
        scripts = IntlFingerprint.get_all_scripts(fi)
        assert len(scripts) >= 1
        assert all(isinstance(s, str) for s in scripts)


# ═══════════════════════════════════════════════════════════
# Validator Tests
# ═══════════════════════════════════════════════════════════

class TestGeoConsistencyValidator:
    def test_perfect_finland_profile(self):
        report = GeoConsistencyValidator.validate(
            country_code="FI",
            timezone="Europe/Helsinki",
            languages=["fi", "en-US", "en"],
            accept_language="fi,en-US;q=0.9,en;q=0.8",
            timezone_offset=-120,
            currency="EUR",
            keyboard_layout="fi",
        )
        assert report.is_consistent
        assert report.score == 100
        assert report.checked_fields == 6

    def test_wrong_timezone(self):
        report = GeoConsistencyValidator.validate(
            country_code="FI",
            timezone="America/New_York",
        )
        assert not report.is_consistent
        assert len(report.critical_issues) > 0
        assert report.score < 100

    def test_wrong_language(self):
        report = GeoConsistencyValidator.validate(
            country_code="FI",
            languages=["ja", "en"],
        )
        assert not report.is_consistent

    def test_us_multi_timezone_valid(self):
        report = GeoConsistencyValidator.validate(
            country_code="US",
            timezone="America/Los_Angeles",
            timezone_offset=480,
        )
        assert report.is_consistent

    def test_unknown_country(self):
        report = GeoConsistencyValidator.validate(country_code="XX")
        assert report.score == 50
        assert len(report.issues) == 1

    def test_summary_format(self):
        report = GeoConsistencyValidator.validate(
            country_code="FI",
            timezone="America/New_York",
        )
        summary = report.summary()
        assert "FI" in summary

    def test_to_dict(self):
        report = GeoConsistencyValidator.validate(
            country_code="FI",
            timezone="Europe/Helsinki",
        )
        d = report.to_dict()
        assert "country_code" in d
        assert "score" in d
        assert "issues" in d


# ═══════════════════════════════════════════════════════════
# Engine Tests
# ═══════════════════════════════════════════════════════════

class TestGeoConsistencyEngine:
    def test_singleton_exists(self):
        assert geo_engine is not None
        assert isinstance(geo_engine, GeoConsistencyEngine)

    def test_version(self):
        assert "TITAN" in GeoConsistencyEngine.VERSION

    def test_get_locale(self):
        engine = GeoConsistencyEngine()
        locale = engine.get_locale("FI")
        assert locale is not None
        assert locale.country_code == "FI"

    def test_get_locale_unknown(self):
        engine = GeoConsistencyEngine()
        assert engine.get_locale("XX") is None

    def test_list_countries(self):
        engine = GeoConsistencyEngine()
        countries = engine.list_countries()
        assert "FI" in countries
        assert "US" in countries
        assert len(countries) == 20

    def test_list_regions(self):
        engine = GeoConsistencyEngine()
        regions = engine.list_regions()
        assert "nordic" in regions
        assert "FI" in regions["nordic"]

    def test_build_profile_finland(self):
        engine = GeoConsistencyEngine()
        profile = engine.build_profile("FI")
        assert profile["country_code"] == "FI"
        assert profile["timezone"] == "Europe/Helsinki"
        assert profile["currency"] == "EUR"
        assert "fi" in profile["languages"]
        assert profile["playwright_locale"] == "fi"
        assert len(profile["intl_override_scripts"]) >= 1

    def test_build_profile_us_pacific(self):
        engine = GeoConsistencyEngine()
        profile = engine.build_profile("US", timezone_variant="pacific")
        assert profile["timezone"] == "America/Los_Angeles"
        assert profile["timezone_offset"] == 480

    def test_build_profile_unknown_fallback(self):
        engine = GeoConsistencyEngine()
        profile = engine.build_profile("XX")
        # Falls back to US locale data but keeps original country_code
        assert profile["timezone"] == "America/New_York"
        assert profile["currency"] == "USD"

    def test_build_playwright_context_args(self):
        engine = GeoConsistencyEngine()
        args = engine.build_playwright_context_args("FI")
        assert args["locale"] == "fi"
        assert args["timezone_id"] == "Europe/Helsinki"
        assert "Accept-Language" in args["extra_http_headers"]

    def test_select_random_country(self):
        engine = GeoConsistencyEngine()
        country = engine.select_random_country()
        assert country in GEO_DATABASE

    def test_select_random_country_by_region(self):
        engine = GeoConsistencyEngine()
        country = engine.select_random_country(region=Region.NORDIC)
        assert country in ["FI", "SE", "NO", "DK"]

    def test_match_country_to_proxy(self):
        engine = GeoConsistencyEngine()
        profile = engine.match_country_to_proxy("FI")
        assert profile["country_code"] == "FI"

    def test_match_unknown_proxy(self):
        engine = GeoConsistencyEngine()
        profile = engine.match_country_to_proxy("XX")
        assert profile["country_code"] in GEO_DATABASE

    def test_validate(self):
        engine = GeoConsistencyEngine()
        report = engine.validate("FI", timezone="Europe/Helsinki")
        assert report.score == 100

    def test_get_stats(self):
        engine = GeoConsistencyEngine()
        engine.build_profile("FI")
        engine.validate("FI")
        stats = engine.get_stats()
        assert stats["supported_countries"] == 20
        assert stats["profiles_generated"] >= 1
        assert stats["validations_run"] >= 1

    def test_randomize_quality(self):
        engine = GeoConsistencyEngine()
        profile = engine.build_profile("FI", randomize_quality=0.5)
        assert "q=" in profile["accept_language"]


