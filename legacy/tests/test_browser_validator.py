
"""Tests for utils/browser_validator.py — Live Browser Fingerprint Validator."""


import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.browser_validator import (
    ValidationTarget, ValidationCheck, ValidationReport,
    CheckStatus, VALIDATION_URLS, BrowserValidator, browser_validator,
)


# ═══════════════════════════════════════════════════════════
# Validation Target Tests
# ═══════════════════════════════════════════════════════════

class TestValidationTargets:
    def test_all_targets_have_urls(self):
        for target in ValidationTarget:
            assert target in VALIDATION_URLS, f"Missing URL for {target}"

    def test_urls_are_https(self):
        for target, url in VALIDATION_URLS.items():
            assert url.startswith("https://"), f"{target} URL not HTTPS: {url}"

    def test_target_count(self):
        assert len(ValidationTarget) == 10


# ═══════════════════════════════════════════════════════════
# ValidationCheck Tests
# ═══════════════════════════════════════════════════════════

class TestValidationCheck:
    def test_create_pass(self):
        c = ValidationCheck(name="test", target="x", status=CheckStatus.PASS, score=10)
        assert c.status_code == CheckStatus.PASS
        assert c.score == 10

    def test_create_fail(self):
        c = ValidationCheck(name="test", target="x", status=CheckStatus.FAIL, details="bad")
        assert c.status_code == CheckStatus.FAIL
        assert c.details == "bad"

    def test_to_dict(self):
        c = ValidationCheck(name="webdriver", target="navigator", status=CheckStatus.PASS, score=15)
        d = c.to_dict()
        assert d["name"] == "webdriver"
        assert d["status"] == "pass"
        assert d["score"] == 15


# ═══════════════════════════════════════════════════════════
# ValidationReport Tests
# ═══════════════════════════════════════════════════════════

class TestValidationReport:
    def test_empty_report(self):
        r = ValidationReport()
        assert r.passed == 0
        assert r.failed == 0
        assert r.total == 0
        assert r.overall_score == 0

    def test_report_with_checks(self):
        r = ValidationReport(
            checks=[
                ValidationCheck("a", "x", CheckStatus.PASS, score=10),
                ValidationCheck("b", "x", CheckStatus.PASS, score=10),
                ValidationCheck("c", "x", CheckStatus.FAIL, score=0),
                ValidationCheck("d", "x", CheckStatus.SKIP),
            ]
        )
        assert r.passed == 2
        assert r.failed == 1
        assert r.total == 3  # Skip not counted

    def test_summary_format(self):
        r = ValidationReport(
            overall_score=85,
            duration_seconds=3.5,
            checks=[
                ValidationCheck("webdriver", "nav", CheckStatus.PASS, details="hidden ✓", score=15),
                ValidationCheck("chrome", "win", CheckStatus.FAIL, details="missing!", score=0),
            ],
        )
        s = r.summary()
        assert "85/100" in s
        assert "hidden ✓" in s
        assert "missing!" in s

    def test_to_dict(self):
        r = ValidationReport(
            timestamp=1000, overall_score=90, duration_seconds=2.0,
            checks=[ValidationCheck("a", "b", CheckStatus.PASS, score=10)],
            warnings=["test warning"],
        )
        d = r.to_dict()
        assert d["overall_score"] == 90
        assert d["passed"] == 1
        assert d["warnings"] == ["test warning"]


# ═══════════════════════════════════════════════════════════
# BrowserValidator Tests
# ═══════════════════════════════════════════════════════════

class TestBrowserValidator:
    def test_singleton_exists(self):
        assert browser_validator is not None

    def test_checks_defined(self):
        assert len(BrowserValidator.CHECKS) >= 10

    def test_check_weights_sum(self):
        total = sum(w for _, _, w in BrowserValidator.CHECKS)
        assert total > 80  # Should be meaningful total

    def test_check_names_unique(self):
        names = [n for n, _, _ in BrowserValidator.CHECKS]
        assert len(names) == len(set(names))


# ═══════════════════════════════════════════════════════════
# CheckStatus Tests
# ═══════════════════════════════════════════════════════════

class TestCheckStatus:
    def test_all_statuses(self):
        assert CheckStatus.PASS.value == "pass"
        assert CheckStatus.WARN.value == "warn"
        assert CheckStatus.FAIL.value == "fail"
        assert CheckStatus.SKIP.value == "skip"
        assert CheckStatus.ERROR.value == "error"

    def test_status_count(self):
        assert len(CheckStatus) == 5


