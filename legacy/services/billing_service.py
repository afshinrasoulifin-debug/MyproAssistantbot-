
from __future__ import annotations
"""
tg_bot/services/billing_service.py — Subscription & Billing v9.3
Handles: subscriptions, billing, referrals, coupons, trials, usage-based pricing.
"""
import logging
import time
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

# ── TITANIUM v29.0 Integration ──


# ── Infrastructure access ──
try:
    from arki_project.services.infra_bridge import get_service_bridge 
except ImportError:
    _get_svc_infra = lambda: None


logger = logging.getLogger(__name__)


class PlanTier(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class Plan:
    tier: PlanTier
    name: str
    price_monthly: float = 0.0
    max_messages_day: int = 50
    max_tokens_day: int = 100000
    features: List[str] = field(default_factory=list)
    ai_models: List[str] = field(default_factory=list)


@dataclass
class Subscription:
    user_id: int
    plan: PlanTier = PlanTier.FREE
    started_at: float = 0.0
    expires_at: float = 0.0
    is_trial: bool = False
    trial_days: int = 7
    auto_renew: bool = False
    payment_method: str = ""  # "telegram_stars", "stripe"


@dataclass
class Referral:
    referrer_id: int
    referred_id: int
    code: str
    reward_given: bool = False
    created_at: float = 0.0


@dataclass
class Coupon:
    code: str
    discount_pct: float = 0.0
    max_uses: int = 100
    used_count: int = 0
    expires_at: float = 0.0
    valid: bool = True


PLANS = {
    PlanTier.FREE: Plan(
        tier=PlanTier.FREE, name="رایگان", price_monthly=0,
        max_messages_day=50, max_tokens_day=100000,
        features=["چت AI", "جستجوی وب", "تولید محتوا"],
        ai_models=["gemini-2.5-pro", "llama-3.3-70b"],
    ),
    PlanTier.PRO: Plan(
        tier=PlanTier.PRO, name="حرفه‌ای", price_monthly=9.99,
        max_messages_day=999999, max_tokens_day=999999999,
        features=["همه ویژگی‌های رایگان", "مدل‌های پیشرفته", "Agent نامحدود",
                   "تحلیل پیشرفته", "API دسترسی", "اولویت پشتیبانی"],
        ai_models=["gemini-2.5-pro", "gpt-4o", "claude-3.5-sonnet"],
    ),
    PlanTier.ENTERPRISE: Plan(
        tier=PlanTier.ENTERPRISE, name="سازمانی", price_monthly=49.99,
        max_messages_day=999999, max_tokens_day=999999999,
        features=["همه ویژگی‌های حرفه‌ای", "White-label", "SLA 99.9%",
                   "پشتیبانی اختصاصی", "On-premise", "Custom models"],
        ai_models=["all"],
    ),
}


class BillingService:
    # NOTE: All methods are intentionally sync — they operate on in-memory
    # data structures only (no DB, no I/O). Safe to call from async handlers.
    # If DB backing is added later, convert to async.
    """Manages subscriptions, billing, referrals, and coupons."""

    def __init__(self):
        self._subscriptions: Dict[int, Subscription] = {}
        self._referrals: Dict[str, Referral] = {}
        self._coupons: Dict[str, Coupon] = {}
        self._invoices: List[Dict] = []

    # ── Subscriptions ──

    def get_plan(self, user_id: int) -> Plan:
        sub = self._subscriptions.get(user_id)
        if not sub:
            return PLANS[PlanTier.FREE]
        if sub.expires_at and time.time() > sub.expires_at:
            return PLANS[PlanTier.FREE]
        return PLANS.get(sub.plan, PLANS[PlanTier.FREE])

    def subscribe(self, user_id: int, tier: PlanTier,
                  months: int = 1, payment_method: str = "") -> Subscription:
        now = time.time()
        sub = Subscription(
            user_id=user_id,
            plan=tier,
            started_at=now,
            expires_at=now + months * 30 * 86400,
            payment_method=payment_method,
        )
        self._subscriptions[user_id] = sub
        self._invoices.append({
            "user_id": user_id,
            "plan": tier.value,
            "amount": PLANS[tier].price_monthly * months,
            "months": months,
            "timestamp": now,
        })
        return sub

    def start_trial(self, user_id: int, days: int = 7) -> Subscription:
        now = time.time()
        sub = Subscription(
            user_id=user_id,
            plan=PlanTier.PRO,
            started_at=now,
            expires_at=now + days * 86400,
            is_trial=True,
            trial_days=days,
        )
        self._subscriptions[user_id] = sub
        return sub

    # ── Referrals ──

    def generate_referral_code(self, user_id: int) -> str:
        code = hashlib.md5(f"ref:{user_id}:{time.time()}".encode()).hexdigest()[:8].upper()
        self._referrals[code] = Referral(
            referrer_id=user_id, referred_id=0,
            code=code, created_at=time.time(),
        )
        return code

    def use_referral(self, code: str, referred_id: int) -> bool:
        ref = self._referrals.get(code)
        if not ref or ref.reward_given:
            return False
        ref.referred_id = referred_id
        ref.reward_given = True
        # Give both users trial extension
        self.start_trial(ref.referrer_id, days=14)
        self.start_trial(referred_id, days=14)
        return True

    # ── Coupons ──

    def create_coupon(self, code: str, discount_pct: float,
                      max_uses: int = 100, valid_days: int = 30) -> Coupon:
        coupon = Coupon(
            code=code.upper(),
            discount_pct=discount_pct,
            max_uses=max_uses,
            expires_at=time.time() + valid_days * 86400,
        )
        self._coupons[coupon.code] = coupon
        return coupon

    def apply_coupon(self, code: str) -> Optional[float]:
        coupon = self._coupons.get(code.upper())
        if not coupon or not coupon.valid:
            return None
        if coupon.used_count >= coupon.max_uses:
            return None
        if time.time() > coupon.expires_at:
            coupon.valid = False
            return None
        coupon.used_count += 1
        return coupon.discount_pct

    @property
    def stats(self) -> dict:
        return {
            "total_subscribers": len(self._subscriptions),
            "active_pro": sum(1 for s in self._subscriptions.values()
                            if s.plan == PlanTier.PRO and time.time() < s.expires_at),
            "active_enterprise": sum(1 for s in self._subscriptions.values()
                                   if s.plan == PlanTier.ENTERPRISE and time.time() < s.expires_at),
            "total_referrals": len(self._referrals),
            "total_coupons": len(self._coupons),
            "total_invoices": len(self._invoices),
        }


_service: Optional[BillingService] = None

def get_billing_service() -> BillingService:
    global _service
    if _service is None:
        _service = BillingService()
    return _service


