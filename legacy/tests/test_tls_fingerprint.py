
"""Tests for utils/tls_fingerprint.py — TLS Fingerprint Engine."""


import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.tls_fingerprint import (
    JA3Components, JA4Components, CipherSuite, TLSVersion, TLSResponse,
    GREASEInjector, ALL_TLS_PROFILES,
    CHROME_125_WIN, FIREFOX_126_WIN, SAFARI_17_MAC, EDGE_125_WIN,
    tls_engine,
)


# ═══════════════════════════════════════════════════════════
# JA3 Tests
# ═══════════════════════════════════════════════════════════

class TestJA3:
    def test_compute_hash_returns_md5(self):
        ja3 = JA3Components(
            tls_version=0x0303,
            cipher_suites=[0x1301, 0x1302],
            extensions=[0, 10, 11],
            elliptic_curves=[0x001D, 0x0017],
            ec_point_formats=[0],
        )
        h = ja3.compute_hash()
        assert len(h) == 32  # MD5 hex = 32 chars
        assert all(c in "0123456789abcdef" for c in h)

    def test_ja3_filters_grease(self):
        """GREASE values should be filtered out of JA3."""
        ja3 = JA3Components(
            tls_version=0x0303,
            cipher_suites=[0x0A0A, 0x1301, 0x1302],  # 0x0A0A is GREASE
            extensions=[0x0A0A, 0, 10],
            elliptic_curves=[0x001D],
            ec_point_formats=[0],
        )
        s = ja3.to_string()
        assert "2570" not in s  # 0x0A0A = 2570 decimal

    def test_ja3_deterministic(self):
        """Same components should always produce same hash."""
        ja3a = JA3Components(tls_version=0x0303, cipher_suites=[0x1301])
        ja3b = JA3Components(tls_version=0x0303, cipher_suites=[0x1301])
        assert ja3a.compute_hash() == ja3b.compute_hash()

    def test_ja3_different_ciphers_different_hash(self):
        ja3a = JA3Components(cipher_suites=[0x1301])
        ja3b = JA3Components(cipher_suites=[0x1302])
        assert ja3a.compute_hash() != ja3b.compute_hash()

    def test_ja3_to_string(self):
        ja3 = JA3Components(
            tls_version=771,  # 0x0303
            cipher_suites=[4865, 4866],  # 0x1301, 0x1302
            extensions=[0, 10],
            elliptic_curves=[29],  # 0x001D
            ec_point_formats=[0],
        )
        s = ja3.to_string()
        assert s == "771,4865-4866,0-10,29,0"


# ═══════════════════════════════════════════════════════════
# JA4 Tests
# ═══════════════════════════════════════════════════════════

class TestJA4:
    def test_compute_hash_format(self):
        ja4 = JA4Components(
            protocol="t",
            tls_version="13",
            sni="d",
            cipher_count=5,
            extension_count=10,
            alpn_first="h2",
            cipher_suites_sorted=[0x1301, 0x1302],
            extensions_sorted=[0, 10, 43],
            signature_algorithms=[0x0403, 0x0804],
        )
        h = ja4.compute_hash()
        parts = h.split("_")
        assert len(parts) == 3
        assert parts[0].startswith("t13d")  # protocol + version + sni
        assert len(parts[1]) == 12  # SHA256[:12]
        assert len(parts[2]) == 12

    def test_ja4_deterministic(self):
        ja4 = JA4Components(cipher_suites_sorted=[0x1301], extensions_sorted=[0])
        assert ja4.compute_hash() == ja4.compute_hash()


# ═══════════════════════════════════════════════════════════
# Profile Tests
# ═══════════════════════════════════════════════════════════

class TestProfiles:
    def test_all_profiles_registered(self):
        assert len(ALL_TLS_PROFILES) == 5

    def test_chrome_profile_has_tls13(self):
        assert TLSVersion.TLS_1_3.value in CHROME_125_WIN.supported_versions

    def test_chrome_has_h2_alpn(self):
        assert "h2" in CHROME_125_WIN.alpn_protocols

    def test_firefox_different_from_chrome(self):
        """Firefox cipher order differs from Chrome."""
        # Firefox puts CHACHA20 second, Chrome puts it third
        chrome_third = CHROME_125_WIN.cipher_suites[2]
        firefox_second = FIREFOX_126_WIN.cipher_suites[1]
        assert chrome_third == firefox_second == CipherSuite.CHACHA20_POLY1305_SHA256

    def test_safari_fewer_extensions(self):
        assert len(SAFARI_17_MAC.extensions) < len(CHROME_125_WIN.extensions)

    def test_edge_matches_chrome_ja3(self):
        """Edge is Chromium-based, same JA3 as Chrome."""
        assert EDGE_125_WIN.ja3_hash == CHROME_125_WIN.ja3_hash

    def test_profile_ja3_computable(self):
        for name, profile in ALL_TLS_PROFILES.items():
            ja3 = profile.get_ja3()
            h = ja3.compute_hash()
            assert len(h) == 32, f"Profile {name} JA3 hash invalid"

    def test_all_profiles_have_curl_impersonate(self):
        for name, profile in ALL_TLS_PROFILES.items():
            assert profile.curl_impersonate, f"Profile {name} missing curl_impersonate"


# ═══════════════════════════════════════════════════════════
# Engine Tests
# ═══════════════════════════════════════════════════════════

class TestTLSEngine:
    def test_singleton_exists(self):
        assert tls_engine is not None

    def test_get_best_backend(self):
        backend = tls_engine.get_best_backend()
        assert backend in ("curl_cffi", "tls_client", "fallback")

    def test_select_profile_chrome(self):
        p = tls_engine.select_profile("chrome", "windows")
        assert p.browser == "chrome"

    def test_select_profile_firefox(self):
        p = tls_engine.select_profile("firefox", "windows")
        assert p.browser == "firefox"

    def test_select_profile_safari(self):
        p = tls_engine.select_profile("safari", "macos")
        assert p.browser == "safari"

    def test_select_profile_default(self):
        p = tls_engine.select_profile("unknown", "unknown")
        # Falls back to default
        assert p is not None

    def test_compute_ja3(self):
        h = tls_engine.compute_ja3(CHROME_125_WIN)
        assert len(h) == 32

    def test_compute_ja4(self):
        h = tls_engine.compute_ja4(CHROME_125_WIN)
        assert "_" in h

    def test_validate_ja3_match(self):
        h = tls_engine.compute_ja3(CHROME_125_WIN)
        assert tls_engine.validate_ja3(CHROME_125_WIN, h)

    def test_validate_ja3_mismatch(self):
        assert not tls_engine.validate_ja3(CHROME_125_WIN, "0000000000000000")

    def test_stats(self):
        stats = tls_engine.get_stats()
        assert "backend" in stats
        assert "profiles" in stats
        assert stats["profiles"] == 5


# ═══════════════════════════════════════════════════════════
# GREASE Injector Tests
# ═══════════════════════════════════════════════════════════

class TestGREASE:
    def test_random_grease_is_grease(self):
        g = GREASEInjector.get_random_grease()
        assert g in CipherSuite.GREASE_VALUES

    def test_inject_ciphers_adds_one(self):
        ciphers = [0x1301, 0x1302]
        result = GREASEInjector.inject_into_ciphers(ciphers, 0)
        assert len(result) == 3
        assert result[0] in CipherSuite.GREASE_VALUES

    def test_inject_extensions_adds_at_indices(self):
        exts = [0, 10, 11, 43]
        result = GREASEInjector.inject_into_extensions(exts, [0, 2])
        assert len(result) == 6

    def test_inject_does_not_modify_original(self):
        original = [0x1301, 0x1302]
        GREASEInjector.inject_into_ciphers(original, 0)
        assert len(original) == 2


# ═══════════════════════════════════════════════════════════
# TLSResponse Tests
# ═══════════════════════════════════════════════════════════

class TestTLSResponse:
    def test_ok_true(self):
        r = TLSResponse(status_code=200, headers={}, text="ok", content=b"ok", url="https://x.com")
        assert r.ok

    def test_ok_false(self):
        r = TLSResponse(status_code=403, headers={}, text="", content=b"", url="https://x.com")
        assert not r.ok

    def test_json(self):
        r = TLSResponse(status_code=200, headers={}, text='{"a":1}', content=b'{"a":1}', url="")
        assert r.json() == {"a": 1}


# ═══════════════════════════════════════════════════════════
# CipherSuite Constants Tests
# ═══════════════════════════════════════════════════════════

class TestConstants:
    def test_tls13_ciphers(self):
        assert CipherSuite.AES_128_GCM_SHA256 == 0x1301
        assert CipherSuite.AES_256_GCM_SHA384 == 0x1302
        assert CipherSuite.CHACHA20_POLY1305_SHA256 == 0x1303

    def test_grease_values_count(self):
        assert len(CipherSuite.GREASE_VALUES) == 16

    def test_tls_versions(self):
        assert TLSVersion.TLS_1_3.value == 0x0304
        assert TLSVersion.TLS_1_2.value == 0x0303


