
"""Tests for billing/subscription flow."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



class TestBillingService:
    def test_default_plan_is_free(self):
        from services.billing_service import get_billing_service, PlanTier
        billing = get_billing_service()
        plan = billing.get_plan(999999)
        assert plan.tier == PlanTier.FREE

    def test_start_trial(self):
        from services.billing_service import get_billing_service, PlanTier
        billing = get_billing_service()
        sub = billing.start_trial(888888, days=7)
        assert sub.is_trial
        assert sub.plan == PlanTier.PRO
        plan = billing.get_plan(888888)
        assert plan.tier == PlanTier.PRO

    def test_referral_code(self):
        from services.billing_service import get_billing_service
        billing = get_billing_service()
        code = billing.generate_referral_code(777777)
        assert len(code) == 8
        assert code == code.upper(), "Referral code should be uppercased"
        assert code.isalnum(), "Referral code should be alphanumeric"

    def test_use_referral(self):
        from services.billing_service import get_billing_service
        billing = get_billing_service()
        code = billing.generate_referral_code(666666)
        result = billing.use_referral(code, 555555)
        assert result is True
        # Can't reuse
        result2 = billing.use_referral(code, 444444)
        assert result2 is False

    def test_coupon(self):
        from services.billing_service import get_billing_service
        billing = get_billing_service()
        billing.create_coupon("TEST50", 50.0, max_uses=2)
        discount = billing.apply_coupon("TEST50")
        assert discount == 50.0
        discount2 = billing.apply_coupon("TEST50")
        assert discount2 == 50.0
        # Third use should fail (max_uses=2)
        discount3 = billing.apply_coupon("TEST50")
        assert discount3 is None

    def test_invalid_coupon(self):
        from services.billing_service import get_billing_service
        billing = get_billing_service()
        assert billing.apply_coupon("NONEXISTENT") is None


class TestBillingStats:
    def test_stats(self):
        from services.billing_service import get_billing_service
        billing = get_billing_service()
        stats = billing.stats
        assert "total_subscribers" in stats
        assert "total_referrals" in stats


