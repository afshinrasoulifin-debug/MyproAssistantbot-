
from __future__ import annotations
"""tests/test_outreach_engine.py — Outreach Engine Tests"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from datetime import datetime, timezone

@pytest.fixture
def outreach():
    from utils.outreach_engine import OutreachEngine
    return OutreachEngine(daily_limit=50, ai_client=None)

class TestInit:
    def test_creates(self, outreach):
        assert outreach._daily_limit == 50

    def test_initial_count_zero(self, outreach):
        assert outreach._emails_sent_today == 0

    def test_daily_limit_not_reached(self, outreach):
        assert outreach._daily_limit_reached() is False

    def test_daily_limit_reached(self, outreach):
        outreach._today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        outreach._emails_sent_today = 50
        assert outreach._daily_limit_reached() is True

    def test_stats(self, outreach):
        stats = outreach.get_stats()
        assert stats["daily_limit"] == 50

class TestEmailContent:
    def test_dataclass(self):
        from utils.outreach_engine import EmailContent
        ec = EmailContent(subject="Test", body_html="<p>Hello</p>", language="en")
        assert ec.subject == "Test"

class TestOutreachResult:
    def test_to_dict(self):
        from utils.outreach_engine import OutreachResult
        r = OutreachResult(emails_generated=5, emails_sent=3, emails_failed=2)
        d = r.to_dict()
        assert d["emails_sent"] == 3 and d["emails_failed"] == 2

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


