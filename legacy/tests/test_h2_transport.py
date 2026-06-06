
"""Tests for utils/h2_transport.py — HTTP/2 Transport Fingerprint Engine."""

import struct

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.h2_transport import (
    H2Setting, H2TransportProfile,
    CHROME_125_H2, FIREFOX_126_H2, SAFARI_17_H2, EDGE_125_H2,
    ALL_H2_PROFILES, H2HeaderOrderer, H2SettingsBuilder,
    H2FingerprintValidator, H2ConnectionPreface, H2ProfileSelector,
    h2_profile_selector,
)


# ═══════════════════════════════════════════════════════════
# Profile Tests
# ═══════════════════════════════════════════════════════════

class TestProfiles:
    def test_all_profiles_registered(self):
        assert len(ALL_H2_PROFILES) == 4

    def test_chrome_disables_push(self):
        settings = dict(CHROME_125_H2.settings_order)
        assert settings[H2Setting.ENABLE_PUSH.value] == 0

    def test_chrome_window_update(self):
        assert CHROME_125_H2.connection_window_update == 15663105

    def test_firefox_window_update(self):
        assert FIREFOX_126_H2.connection_window_update == 12517377

    def test_safari_uses_priority_frames(self):
        assert SAFARI_17_H2.uses_priority_frames is True

    def test_chrome_no_priority_frames(self):
        assert CHROME_125_H2.uses_priority_frames is False

    def test_chrome_uses_priority_update(self):
        assert CHROME_125_H2.uses_priority_update is True

    def test_safari_hpack_table_size(self):
        assert SAFARI_17_H2.hpack_table_size == 4096

    def test_chrome_hpack_table_size(self):
        assert CHROME_125_H2.hpack_table_size == 65536

    def test_edge_matches_chrome(self):
        assert EDGE_125_H2.settings_order == CHROME_125_H2.settings_order
        assert EDGE_125_H2.connection_window_update == CHROME_125_H2.connection_window_update


# ═══════════════════════════════════════════════════════════
# Pseudo-Header Order Tests
# ═══════════════════════════════════════════════════════════

class TestPseudoHeaderOrder:
    def test_chrome_order(self):
        assert CHROME_125_H2.pseudo_header_order == [":method", ":authority", ":scheme", ":path"]

    def test_firefox_order(self):
        assert FIREFOX_126_H2.pseudo_header_order == [":method", ":path", ":authority", ":scheme"]

    def test_safari_order(self):
        assert SAFARI_17_H2.pseudo_header_order == [":method", ":scheme", ":path", ":authority"]

    def test_all_contain_same_headers(self):
        expected = {":method", ":authority", ":scheme", ":path"}
        for name, profile in ALL_H2_PROFILES.items():
            assert set(profile.pseudo_header_order) == expected, f"Profile {name} missing pseudo-headers"


# ═══════════════════════════════════════════════════════════
# Header Orderer Tests
# ═══════════════════════════════════════════════════════════

class TestHeaderOrderer:
    def test_order_headers_chrome(self):
        headers = {
            "accept-language": "en-US",
            "user-agent": "Chrome/125",
            "accept": "text/html",
            "cookie": "session=abc",
        }
        ordered = H2HeaderOrderer.order_headers(headers, CHROME_125_H2)
        keys = [k for k, v in ordered]
        # Chrome order: user-agent before accept before accept-language
        ua_idx = keys.index("user-agent")
        accept_idx = keys.index("accept")
        assert ua_idx < accept_idx

    def test_order_preserves_all_headers(self):
        headers = {"x-custom": "val", "user-agent": "test", "accept": "*/*"}
        ordered = H2HeaderOrderer.order_headers(headers, CHROME_125_H2)
        assert len(ordered) == 3

    def test_unknown_headers_appended(self):
        headers = {"x-unknown-header": "value"}
        ordered = H2HeaderOrderer.order_headers(headers, CHROME_125_H2)
        assert ("x-unknown-header", "value") in ordered

    def test_pseudo_headers_chrome(self):
        ordered = H2HeaderOrderer.order_pseudo_headers(
            "GET", "example.com", "https", "/", CHROME_125_H2,
        )
        assert ordered[0] == (":method", "GET")
        assert ordered[1] == (":authority", "example.com")

    def test_pseudo_headers_firefox(self):
        ordered = H2HeaderOrderer.order_pseudo_headers(
            "GET", "example.com", "https", "/page", FIREFOX_126_H2,
        )
        assert ordered[0] == (":method", "GET")
        assert ordered[1] == (":path", "/page")


# ═══════════════════════════════════════════════════════════
# Settings Builder Tests
# ═══════════════════════════════════════════════════════════

class TestSettingsBuilder:
    def test_build_payload_length(self):
        payload = H2SettingsBuilder.build_settings_payload(CHROME_125_H2)
        # Each setting = 6 bytes (2 ID + 4 value)
        assert len(payload) == 6 * len(CHROME_125_H2.settings_order)

    def test_build_payload_content(self):
        payload = H2SettingsBuilder.build_settings_payload(CHROME_125_H2)
        # First setting: HEADER_TABLE_SIZE (1) = 65536
        setting_id, value = struct.unpack("!HI", payload[:6])
        assert setting_id == 1
        assert value == 65536

    def test_window_update_payload(self):
        payload = H2SettingsBuilder.build_window_update_payload(CHROME_125_H2)
        assert len(payload) == 4
        value = struct.unpack("!I", payload)[0]
        assert value == 15663105

    def test_settings_dict(self):
        d = H2SettingsBuilder.get_settings_dict(CHROME_125_H2)
        assert isinstance(d, dict)
        assert d[1] == 65536  # HEADER_TABLE_SIZE

    def test_safari_priority_frames(self):
        frames = H2SettingsBuilder.build_priority_frames(SAFARI_17_H2)
        assert len(frames) > 0

    def test_chrome_no_priority_frames(self):
        frames = H2SettingsBuilder.build_priority_frames(CHROME_125_H2)
        assert len(frames) == 0


# ═══════════════════════════════════════════════════════════
# Validator Tests
# ═══════════════════════════════════════════════════════════

class TestValidator:
    def test_chrome_valid(self):
        issues = H2FingerprintValidator.validate(CHROME_125_H2)
        assert len(issues) == 0

    def test_firefox_valid(self):
        issues = H2FingerprintValidator.validate(FIREFOX_126_H2)
        assert len(issues) == 0

    def test_safari_valid(self):
        issues = H2FingerprintValidator.validate(SAFARI_17_H2)
        assert len(issues) == 0

    def test_score_chrome_perfect(self):
        score = H2FingerprintValidator.score(CHROME_125_H2)
        assert score == 100

    def test_invalid_profile_detects_issues(self):
        bad = H2TransportProfile(
            name="bad_chrome",
            browser="chrome",
            version="125",
            connection_window_update=100,  # Way too low for Chrome
            pseudo_header_order=[":method", ":path", ":scheme", ":authority"],  # Firefox order!
            uses_priority_frames=True,  # Chrome doesn't use PRIORITY
        )
        issues = H2FingerprintValidator.validate(bad)
        assert len(issues) >= 2  # Window + priority + pseudo-header


# ═══════════════════════════════════════════════════════════
# Connection Preface Tests
# ═══════════════════════════════════════════════════════════

class TestConnectionPreface:
    def test_magic_string(self):
        assert H2ConnectionPreface.MAGIC == b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"

    def test_chrome_preface_frames(self):
        frames = H2ConnectionPreface.build(CHROME_125_H2)
        assert len(frames) >= 2  # SETTINGS + WINDOW_UPDATE
        assert frames[0]["type"] == "SETTINGS"
        assert frames[1]["type"] == "WINDOW_UPDATE"

    def test_safari_preface_includes_priority(self):
        frames = H2ConnectionPreface.build(SAFARI_17_H2)
        types = [f["type"] for f in frames]
        assert "PRIORITY" in types

    def test_firefox_preface(self):
        frames = H2ConnectionPreface.build(FIREFOX_126_H2)
        assert frames[0]["type"] == "SETTINGS"


# ═══════════════════════════════════════════════════════════
# Profile Selector Tests
# ═══════════════════════════════════════════════════════════

class TestProfileSelector:
    def test_select_chrome(self):
        p = H2ProfileSelector.select("chrome")
        assert p.browser == "chrome"

    def test_select_firefox(self):
        p = H2ProfileSelector.select("Firefox")
        assert p.browser == "firefox"

    def test_select_safari(self):
        p = H2ProfileSelector.select("safari")
        assert p.browser == "safari"

    def test_select_edge(self):
        p = H2ProfileSelector.select("edge")
        assert p.browser == "chrome"  # Edge uses Chrome H2

    def test_select_by_ua_chrome(self):
        p = H2ProfileSelector.select_by_ua(
            "Mozilla/5.0 (Windows NT 10.0) Chrome/125.0.0.0 Safari/537.36"
        )
        assert p.browser == "chrome"

    def test_select_by_ua_firefox(self):
        p = H2ProfileSelector.select_by_ua(
            "Mozilla/5.0 (Windows NT 10.0; rv:126.0) Gecko/20100101 Firefox/126.0"
        )
        assert p.browser == "firefox"

    def test_select_by_ua_safari(self):
        p = H2ProfileSelector.select_by_ua(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15"
        )
        assert p.browser == "safari"

    def test_singleton_exists(self):
        assert h2_profile_selector is not None


