
from __future__ import annotations
from arki_project.exceptions import CallbackError, HandlerError
"""
tg_bot/handlers/payment_handler.py — Payment & Subscription v9.5
Full payment flow: Stripe + Telegram Stars + Trial.
"""
import logging
import os
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup,
    LabeledPrice, PreCheckoutQuery,
)
from arki_project.utils.safe_send import safe_reply, safe_answer_callback

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config 
except ImportError:
    pass
logger = logging.getLogger(__name__)
router = Router(name="payment")

PLANS = {
    "free": {"name": "رایگان", "price": 0, "daily_tokens": 5000, "models": 3},
    "pro": {"name": "حرفه‌ای", "price": 990, "daily_tokens": 50000, "models": 19},
    "business": {"name": "بیزنسی", "price": 2990, "daily_tokens": 200000, "models": 59},
    "enterprise": {"name": "سازمانی", "price": 9990, "daily_tokens": 1000000, "models": 59},
}


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message) -> None:
    """Show subscription plans."""
    user_id = message.from_user.id if message.from_user else 0

    plans_text = "\n".join(
        f"{'🟢' if k == 'free' else '🔵' if k == 'pro' else '🟡' if k == 'business' else '💎'} "
        f"*{v['name']}* — {v['price']:,} تومان/ماه\n"
        f"   توکن روزانه: {v['daily_tokens']:,} | مدل‌ها: {v['models']}"
        for k, v in PLANS.items()
    )

    buttons = [
        [InlineKeyboardButton(text=f"{v['name']} — {v['price']:,} تومان", callback_data=f"plan:{k}")]
        for k, v in PLANS.items() if k != "free"
    ]
    buttons.append([InlineKeyboardButton(text="🎁 تست رایگان ۷ روزه", callback_data="plan:trial")])

    await safe_reply(message,
        f"💳 *پلن‌های اشتراک آرکی*\n\n{plans_text}\n\n"
        "پلن مورد نظر خود را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(lambda c: c.data and c.data.startswith("plan:"))
async def handle_plan_selection(callback: CallbackQuery) -> None:
    """Handle plan selection."""
    plan_key = callback.data.split(":")[1] if callback.data else ""
    user_id = callback.from_user.id

    if plan_key == "trial":
        # Activate 7-day trial
        try:
            from arki_project.services.billing_service import get_billing_service
            billing = get_billing_service()
            await billing.activate_trial(user_id, days=7)
            await safe_answer_callback(callback, "🎁 تست ۷ روزه فعال شد!")
            await callback.message.answer(
                "✅ *پلن آزمایشی فعال شد!*\n"
                "مدت: ۷ روز\n"
                "سطح دسترسی: Pro\n\n"
                "از تمام امکانات لذت ببرید! 🚀"
            )
        except HandlerError as e:
            logger.error("Trial activation failed: %s", e)
            await safe_answer_callback(callback, "❌ خطا در فعال‌سازی")
        return

    plan = PLANS.get(plan_key)
    if not plan:
        await safe_answer_callback(callback, "❌ پلن نامعتبر")
        return

    # Try Stripe payment
    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if stripe_key:
        try:
            import stripe
            stripe.api_key = stripe_key

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"Arki {plan['name']}"},
                        "unit_amount": plan["price"],
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }],
                mode="subscription",
                metadata={"user_id": str(user_id), "plan": plan_key},
                success_url="https://t.me/arki_bot?start=payment_success",
                cancel_url="https://t.me/arki_bot?start=payment_cancel",
            )

            await callback.message.answer(
                f"💳 *پرداخت {plan['name']}*\n\n"
                f"[کلیک برای پرداخت]({session.url})",
                parse_mode="Markdown"
            )
            await safe_answer_callback(callback, "")
            return
        except ImportError:
            logger.warning("Stripe SDK not installed")
        except HandlerError as e:
            logger.error("Stripe error: %s", e)

    # Fallback: Telegram Stars payment
    try:
        prices = [LabeledPrice(label=plan["name"], amount=plan["price"])]
        await callback.message.answer_invoice(
            title=f"اشتراک {plan['name']}",
            description=f"اشتراک ماهانه پلن {plan['name']} آرکی",
            payload=f"sub_{plan_key}_{user_id}",
            provider_token="",  # Telegram Stars
            currency="XTR",
            prices=prices,
        )
        await safe_answer_callback(callback, "")
    except CallbackError as e:
        logger.error("Invoice error: %s", e)
        await safe_answer_callback(callback, "❌ خطا در ایجاد فاکتور")


@router.pre_checkout_query()
async def handle_pre_checkout(query: PreCheckoutQuery) -> None:
    """Validate payment before processing."""
    payload = query.invoice_payload or ""

    # v9.5: Validate payload format
    if not payload.startswith("sub_"):
        await query.answer(ok=False, error_message="فاکتور نامعتبر")
        return

    parts = payload.split("_")
    if len(parts) < 3:
        await query.answer(ok=False, error_message="فاکتور نامعتبر")
        return

    plan_key = parts[1]
    if plan_key not in PLANS:
        await query.answer(ok=False, error_message="پلن نامعتبر")
        return

    await query.answer(ok=True)


@router.message(lambda m: m.successful_payment is not None)
async def handle_successful_payment(message: Message) -> None:
    """Process successful payment — activate subscription."""
    payment = message.successful_payment
    if not payment:
        return

    user_id = message.from_user.id if message.from_user else 0
    payload = payment.invoice_payload or ""
    parts = payload.split("_")
    plan_key = parts[1] if len(parts) > 1 else "pro"

    try:
        from arki_project.services.billing_service import get_billing_service
        billing = get_billing_service()
        await billing.activate_plan(user_id, plan_key, duration_days=30)

        plan = PLANS.get(plan_key, PLANS["pro"])
        await message.answer(
            "✅ *پرداخت موفق!*\n\n"
            f"📌 پلن: {plan['name']}\n"
            f"💰 مبلغ: {payment.total_amount} {payment.currency}\n"
            "📅 اعتبار: ۳۰ روز\n"
            f"🎯 توکن روزانه: {plan['daily_tokens']:,}\n\n"
            "از آرکی لذت ببرید! 🚀"
        )
    except HandlerError as e:
        logger.error("Payment activation failed: %s", e)
        await message.answer("⚠️ پرداخت ثبت شد اما فعال‌سازی با مشکل مواجه شد. با پشتیبانی تماس بگیرید.")


