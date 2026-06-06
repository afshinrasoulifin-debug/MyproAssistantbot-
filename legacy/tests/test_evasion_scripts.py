
"""
tests/test_evasion_scripts.py — Tests for the 18-script evasion arsenal
═══════════════════════════════════════════════════════════════════════
"""

import sys
import os

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.evasion_scripts import (
    EvasionScriptBuilder,
    WEBDRIVER_EVASION, CDP_EVASION, WEBRTC_LEAK_PREVENTION,
    CANVAS_FINGERPRINT_NOISE, WEBGL_FINGERPRINT_SPOOF,
    AUDIO_FINGERPRINT_NOISE, FONT_ENUMERATION_DEFENSE,
    NAVIGATOR_PROPERTIES_SPOOF, PERMISSIONS_API_EVASION,
    BATTERY_API_SIMULATION, SCREEN_PROPERTIES_MATCH,
    CHROME_RUNTIME_SPOOF, HEADLESS_COUNTERMEASURES,
    IFRAME_DETECTION_PREVENTION, TIMING_ATTACK_PREVENTION,
    CSS_MEDIA_DEFENSE, INPUT_EVENT_CONSISTENCY,
    COOKIE_CONSENT_DISMISS, ALL_SCRIPTS,
)


# ═══════════════════════════════════════════════
# Individual Script Tests
# ═══════════════════════════════════════════════

class TestScriptContent:
    """Verify each evasion script has correct structure."""

    def test_webdriver_evasion_covers_key_properties(self):
        assert "navigator" in WEBDRIVER_EVASION
        assert "webdriver" in WEBDRIVER_EVASION
        assert "__playwright" in WEBDRIVER_EVASION
        assert "_selenium" in WEBDRIVER_EVASION
        assert "ChromeDriverw" in WEBDRIVER_EVASION

    def test_cdp_evasion_covers_devtools(self):
        assert "cdc_adoQpoasnfa76pfcZLmcfl" in CDP_EVASION
        assert "prepareStackTrace" in CDP_EVASION
        assert "Runtime.evaluate" in CDP_EVASION

    def test_webrtc_leak_prevention(self):
        assert "RTCPeerConnection" in WEBRTC_LEAK_PREVENTION
        assert "192.168." in WEBRTC_LEAK_PREVENTION
        assert "icecandidate" in WEBRTC_LEAK_PREVENTION
        assert "STUN" not in WEBRTC_LEAK_PREVENTION or "turn:" in WEBRTC_LEAK_PREVENTION

    def test_canvas_noise_uses_seed(self):
        assert "%CANVAS_SEED%" in CANVAS_FINGERPRINT_NOISE
        assert "seededRandom" in CANVAS_FINGERPRINT_NOISE
        assert "toDataURL" in CANVAS_FINGERPRINT_NOISE
        assert "toBlob" in CANVAS_FINGERPRINT_NOISE
        assert "getImageData" in CANVAS_FINGERPRINT_NOISE

    def test_webgl_spoof_covers_both_contexts(self):
        assert "WebGLRenderingContext" in WEBGL_FINGERPRINT_SPOOF
        assert "WebGL2RenderingContext" in WEBGL_FINGERPRINT_SPOOF
        assert "%WEBGL_VENDOR%" in WEBGL_FINGERPRINT_SPOOF
        assert "%WEBGL_RENDERER%" in WEBGL_FINGERPRINT_SPOOF
        assert "37445" in WEBGL_FINGERPRINT_SPOOF  # UNMASKED_VENDOR_WEBGL
        assert "37446" in WEBGL_FINGERPRINT_SPOOF  # UNMASKED_RENDERER_WEBGL

    def test_audio_noise_covers_offline_ctx(self):
        assert "OfflineAudioContext" in AUDIO_FINGERPRINT_NOISE
        assert "AnalyserNode" in AUDIO_FINGERPRINT_NOISE
        assert "%AUDIO_SEED%" in AUDIO_FINGERPRINT_NOISE

    def test_font_defense_has_proxy(self):
        assert "measureText" in FONT_ENUMERATION_DEFENSE
        assert "Proxy" in FONT_ENUMERATION_DEFENSE
        assert "document.fonts" in FONT_ENUMERATION_DEFENSE

    def test_navigator_spoof_comprehensive(self):
        assert "hardwareConcurrency" in NAVIGATOR_PROPERTIES_SPOOF
        assert "deviceMemory" in NAVIGATOR_PROPERTIES_SPOOF
        assert "maxTouchPoints" in NAVIGATOR_PROPERTIES_SPOOF
        assert "connection" in NAVIGATOR_PROPERTIES_SPOOF
        assert "mimeTypes" in NAVIGATOR_PROPERTIES_SPOOF
        assert "plugins" in NAVIGATOR_PROPERTIES_SPOOF
        assert "%NAV_CONFIG%" in NAVIGATOR_PROPERTIES_SPOOF

    def test_permissions_api_evasion(self):
        assert "permissions" in PERMISSIONS_API_EVASION
        assert "notifications" in PERMISSIONS_API_EVASION
        assert "clipboard" in PERMISSIONS_API_EVASION

    def test_battery_api_simulation(self):
        assert "getBattery" in BATTERY_API_SIMULATION
        assert "%BATTERY_LEVEL%" in BATTERY_API_SIMULATION
        assert "%BATTERY_CHARGING%" in BATTERY_API_SIMULATION

    def test_screen_properties_match(self):
        assert "screen" in SCREEN_PROPERTIES_MATCH
        assert "devicePixelRatio" in SCREEN_PROPERTIES_MATCH
        assert "outerWidth" in SCREEN_PROPERTIES_MATCH
        assert "outerHeight" in SCREEN_PROPERTIES_MATCH
        assert "%SCREEN_CONFIG%" in SCREEN_PROPERTIES_MATCH

    def test_chrome_runtime_spoof(self):
        assert "chrome" in CHROME_RUNTIME_SPOOF
        assert "runtime" in CHROME_RUNTIME_SPOOF
        assert "loadTimes" in CHROME_RUNTIME_SPOOF
        assert "csi" in CHROME_RUNTIME_SPOOF
        assert "PlatformOs" in CHROME_RUNTIME_SPOOF

    def test_headless_countermeasures_covers_vectors(self):
        assert "Notification" in HEADLESS_COUNTERMEASURES
        assert "speechSynthesis" in HEADLESS_COUNTERMEASURES
        assert "mediaDevices" in HEADLESS_COUNTERMEASURES
        assert "pdfViewerEnabled" in HEADLESS_COUNTERMEASURES
        assert "userActivation" in HEADLESS_COUNTERMEASURES

    def test_iframe_detection_prevention(self):
        assert "window.top" in IFRAME_DETECTION_PREVENTION
        assert "frameElement" in IFRAME_DETECTION_PREVENTION

    def test_timing_attack_prevention(self):
        assert "performance.now" in TIMING_ATTACK_PREVENTION
        assert "Date.now" in TIMING_ATTACK_PREVENTION

    def test_css_media_defense(self):
        assert "matchMedia" in CSS_MEDIA_DEFENSE
        assert "prefers-color-scheme" in CSS_MEDIA_DEFENSE
        assert "prefers-reduced-motion" in CSS_MEDIA_DEFENSE
        assert "%COLOR_SCHEME%" in CSS_MEDIA_DEFENSE

    def test_input_event_consistency(self):
        assert "PointerEvent" in INPUT_EVENT_CONSISTENCY
        assert "KeyboardEvent" in INPUT_EVENT_CONSISTENCY
        assert "dispatchEvent" in INPUT_EVENT_CONSISTENCY

    def test_cookie_consent_dismiss(self):
        assert "MutationObserver" in COOKIE_CONSENT_DISMISS
        assert "onetrust" in COOKIE_CONSENT_DISMISS
        assert "CybotCookiebot" in COOKIE_CONSENT_DISMISS
        assert "accept" in COOKIE_CONSENT_DISMISS.lower()


# ═══════════════════════════════════════════════
# Script Builder Tests
# ═══════════════════════════════════════════════

class TestEvasionScriptBuilder:
    """Test the EvasionScriptBuilder assembly logic."""

    def test_build_all_returns_18_scripts(self):
        scripts = EvasionScriptBuilder.build_all()
        assert len(scripts) == 18

    def test_build_all_scripts_are_strings(self):
        scripts = EvasionScriptBuilder.build_all()
        for i, script in enumerate(scripts):
            assert isinstance(script, str), f"Script {i} is not a string"
            assert len(script) > 50, f"Script {i} is suspiciously short"

    def test_build_all_no_unresolved_placeholders(self):
        scripts = EvasionScriptBuilder.build_all()
        for i, script in enumerate(scripts):
            assert "%CANVAS_SEED%" not in script, f"Script {i} has unresolved CANVAS_SEED"
            assert "%AUDIO_SEED%" not in script, f"Script {i} has unresolved AUDIO_SEED"
            assert "%WEBGL_VENDOR%" not in script, f"Script {i} has unresolved WEBGL_VENDOR"
            assert "%WEBGL_RENDERER%" not in script, f"Script {i} has unresolved WEBGL_RENDERER"
            assert "%NAV_CONFIG%" not in script, f"Script {i} has unresolved NAV_CONFIG"
            assert "%SCREEN_CONFIG%" not in script, f"Script {i} has unresolved SCREEN_CONFIG"
            assert "%BATTERY_LEVEL%" not in script, f"Script {i} has unresolved BATTERY_LEVEL"
            assert "%BATTERY_CHARGING%" not in script, f"Script {i} has unresolved BATTERY_CHARGING"
            assert "%COLOR_SCHEME%" not in script, f"Script {i} has unresolved COLOR_SCHEME"

    def test_build_all_custom_config(self):
        scripts = EvasionScriptBuilder.build_all(
            canvas_seed=12345,
            audio_seed=67890,
            webgl_vendor="Test Vendor",
            webgl_renderer="Test Renderer",
            battery_level=0.5,
            color_scheme="dark",
        )
        assert len(scripts) == 18
        # Check that custom values are embedded
        combined = "\n".join(scripts)
        assert "12345" in combined  # canvas seed
        assert "67890" in combined  # audio seed
        assert "Test Vendor" in combined
        assert "Test Renderer" in combined
        assert "0.5" in combined  # battery level
        assert "dark" in combined  # color scheme

    def test_build_minimal_returns_5_scripts(self):
        scripts = EvasionScriptBuilder.build_minimal()
        assert len(scripts) == 5

    def test_build_minimal_includes_essentials(self):
        scripts = EvasionScriptBuilder.build_minimal()
        combined = "\n".join(scripts)
        # Must include webdriver evasion
        assert "webdriver" in combined
        # Must include chrome runtime
        assert "chrome" in combined
        # Must include headless countermeasures
        assert "Notification" in combined

    def test_build_for_cloudflare_returns_9_scripts(self):
        scripts = EvasionScriptBuilder.build_for_cloudflare()
        assert len(scripts) == 9

    def test_build_for_cloudflare_includes_critical_scripts(self):
        scripts = EvasionScriptBuilder.build_for_cloudflare(canvas_seed=999)
        combined = "\n".join(scripts)
        assert "webdriver" in combined
        assert "999" in combined  # canvas seed
        assert "Notification" in combined  # headless countermeasures
        assert "RTCPeerConnection" in combined  # WebRTC prevention
        assert "performance.now" in combined  # timing prevention

    def test_build_all_with_custom_nav_config(self):
        nav = {
            "hardwareConcurrency": 16,
            "deviceMemory": 32,
            "maxTouchPoints": 0,
            "platform": "Linux x86_64",
            "vendor": "Google Inc.",
            "doNotTrack": None,
            "language": "fi-FI",
            "languages": ["fi-FI", "fi", "en"],
            "plugins": [],
        }
        scripts = EvasionScriptBuilder.build_all(nav_config=nav)
        combined = "\n".join(scripts)
        assert "fi-FI" in combined
        assert "16" in combined

    def test_build_all_with_custom_screen_config(self):
        scr = {
            "width": 2560,
            "height": 1440,
            "availWidth": 2560,
            "availHeight": 1400,
            "colorDepth": 30,
            "pixelRatio": 2,
        }
        scripts = EvasionScriptBuilder.build_all(screen_config=scr)
        combined = "\n".join(scripts)
        assert "2560" in combined
        assert "1440" in combined


# ═══════════════════════════════════════════════
# ALL_SCRIPTS Registry Tests
# ═══════════════════════════════════════════════

class TestAllScriptsRegistry:
    """Test the ALL_SCRIPTS discovery dict."""

    def test_all_scripts_has_18_entries(self):
        assert len(ALL_SCRIPTS) == 18

    def test_all_scripts_keys_are_descriptive(self):
        expected_keys = {
            "webdriver_evasion", "cdp_evasion", "webrtc_leak_prevention",
            "canvas_fingerprint_noise", "webgl_fingerprint_spoof",
            "audio_fingerprint_noise", "font_enumeration_defense",
            "navigator_properties_spoof", "permissions_api_evasion",
            "battery_api_simulation", "screen_properties_match",
            "chrome_runtime_spoof", "headless_countermeasures",
            "iframe_detection_prevention", "timing_attack_prevention",
            "css_media_defense", "input_event_consistency",
            "cookie_consent_dismiss",
        }
        assert set(ALL_SCRIPTS.keys()) == expected_keys

    def test_all_scripts_values_are_nonempty_strings(self):
        for name, script in ALL_SCRIPTS.items():
            assert isinstance(script, str), f"{name} is not a string"
            assert len(script) > 100, f"{name} is too short ({len(script)} chars)"

    def test_each_script_is_an_iife(self):
        """Each script should be wrapped in an IIFE (() => { ... })()"""
        for name, script in ALL_SCRIPTS.items():
            stripped = script.strip()
            # Should start with (() => { or similar
            assert stripped.startswith("("), f"{name} doesn't start with IIFE"
            assert stripped.endswith("})();") or stripped.endswith("})();\n"), \
                f"{name} doesn't end with IIFE closure"


