
from __future__ import annotations
"""
Stripe webhook handler — v9.6
Handles subscription events from Stripe.
"""
import logging
import os
import json
from typing import Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


async def stripe_webhook_handler(request: Any) -> Any:
    """Handle Stripe webhook events."""
    from aiohttp import web

    payload = await request.read()
    sig = request.headers.get("Stripe-Signature", "")
    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    try:
        import stripe
        event = stripe.Webhook.construct_event(
            payload, sig, endpoint_secret
        ) if endpoint_secret else json.loads(payload)
    except Exception as e:
        logger.error("Stripe webhook verification failed: %s", e)
        return web.json_response({"error": str(e)}, status=400)

    event_type = event.get("type", "") if isinstance(event, dict) else event.type
    data = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object

    logger.info("Stripe webhook: %s", event_type)

    if event_type == "checkout.session.completed":
        user_id = int(data.get("metadata", {}).get("user_id", 0))
        plan = data.get("metadata", {}).get("plan", "pro")
        if user_id:
            try:
                from arki_project.services.billing_service import get_billing_service
                billing = get_billing_service()
                await billing.activate_plan(user_id, plan, duration_days=30)
                logger.info("Activated plan %s for user %d via Stripe", plan, user_id)
            except Exception as e:
                logger.error("Plan activation failed: %s", e)

    elif event_type == "customer.subscription.deleted":
        # Subscription cancelled
        sub_id = data.get("id", "")
        try:
            from arki_project.services.billing_service import get_billing_service
            billing = get_billing_service()
            await billing.cancel_subscription(sub_id)
            logger.info("Subscription %s cancelled", sub_id)
        except Exception as e:
            logger.error("Subscription cancellation failed: %s", e)

    elif event_type == "invoice.payment_failed":
        user_id = int(data.get("metadata", {}).get("user_id", 0))
        if user_id:
            logger.warning("Payment failed for user %d", user_id)
            # Notification sent via event bus (handled by payment handler)

    return web.json_response({"status": "ok"})


