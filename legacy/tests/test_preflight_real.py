
"""
tests/test_preflight_real.py — Preflight Validation Tests
═══════════════════════════════════════════════════════════
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.preflight import run_preflight, _KNOWN_INSECURE_DEFAULTS

import pytest


class TestPreflightValidation:

    def test_preflight_runs_without_crash(self, monkeypatch):
        monkeypatch.setenv("KMS_MASTER_SECRET", "a-valid-long-secret-for-testing-purposes")
        monkeypatch.setenv("BOT_TOKEN", "test-token")
        result = run_preflight(strict=False)
        assert result.passed or not result.passed  # just runs
        assert len(result.checks) > 0

    def test_detects_missing_kms_secret(self, monkeypatch):
        monkeypatch.delenv("KMS_MASTER_SECRET", raising=False)
        result = run_preflight(strict=False)
        kms_check = next(c for c in result.checks if c["name"] == "KMS_MASTER_SECRET")
        assert kms_check["status"] in ("WARN", "FAIL")

    def test_detects_insecure_default(self, monkeypatch):
        monkeypatch.setenv("KMS_MASTER_SECRET", "arki-default-kms-secret-change-me")
        result = run_preflight(strict=False)
        kms_check = next(c for c in result.checks if c["name"] == "KMS_MASTER_SECRET")
        assert kms_check["status"] == "FAIL"

    def test_detects_apex_env(self, monkeypatch):
        monkeypatch.setenv("INFRA_APEX", "true")
        monkeypatch.setenv("KMS_MASTER_SECRET", "valid-secret-for-testing")
        result = run_preflight(strict=False)
        gm_check = next(c for c in result.checks if c["name"] == "INFRA_APEX")
        assert gm_check["status"] == "FAIL"

    def test_passes_with_good_config(self, monkeypatch):
        monkeypatch.setenv("KMS_MASTER_SECRET", "a-valid-long-secret-for-testing-purposes-12345")
        monkeypatch.delenv("INFRA_APEX", raising=False)
        monkeypatch.setenv("BOT_TOKEN", "good-token")
        monkeypatch.setenv("GEMINI_API_KEY", "good-key")
        result = run_preflight(strict=False)
        assert result.passed

    def test_report_format(self, monkeypatch):
        monkeypatch.setenv("KMS_MASTER_SECRET", "valid-test-secret-longer-than-16")
        result = run_preflight(strict=False)
        report = result.report()
        assert "PRE-FLIGHT" in report
        assert "✅" in report or "⚠️" in report

    def test_known_defaults_list(self):
        assert "changeme" in _KNOWN_INSECURE_DEFAULTS
        assert "default" in _KNOWN_INSECURE_DEFAULTS


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


