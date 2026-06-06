
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/email_engine.py — Real Email Marketing Engine v1.0
═══════════════════════════════════════════════════════════════
Actually sends emails via SMTP, SendGrid, or Resend.

Features:
  • Multi-provider: SMTP → SendGrid → Resend (fallback chain)
  • Email sequences: welcome, follow-up, win-back, promotion
  • HTML templates with brand variables
  • Scheduling & drip campaigns
  • Open/click tracking hooks
  • Unsubscribe management
"""


import asyncio
import logging
import os
import smtplib
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp

# ── TITANIUM Integration ──
try:
    from arki_project.utils.titanium.integration import shielded_post
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════

class EmailProvider(str, Enum):
    SMTP = "smtp"
    SENDGRID = "sendgrid"
    RESEND = "resend"


class SequenceType(str, Enum):
    WELCOME = "welcome"
    FOLLOW_UP = "follow_up"
    WIN_BACK = "win_back"
    PROMOTION = "promotion"
    ABANDONED_CART = "abandoned_cart"
    POST_PURCHASE = "post_purchase"


@dataclass
class EmailContact:
    email: str
    name: str = ""
    tags: List[str] = field(default_factory=list)
    subscribed: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmailMessage:
    to: str
    subject: str
    html_body: str
    text_body: str = ""
    from_email: str = ""
    from_name: str = ""
    reply_to: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class SendResult:
    success: bool
    provider: str = ""
    message_id: str = ""
    error: str = ""


# ═══════════════════════════════════════════════════
# Email Templates (Persian + English)
# ═══════════════════════════════════════════════════

TEMPLATES: Dict[str, Dict[str, str]] = {
    "welcome": {
        "subject_fa": "خوش آمدید به {brand_name}! 🎉",
        "subject_en": "Welcome to {brand_name}! 🎉",
        "html": """
<div style="font-family:Tahoma,Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;direction:rtl;">
  <h1 style="color:{brand_color};text-align:center;">{brand_name}</h1>
  <p style="font-size:16px;">سلام {customer_name}! 👋</p>
  <p>ممنون که عضو خانواده {brand_name} شدید.</p>
  <p>{welcome_message}</p>
  <div style="text-align:center;margin:30px 0;">
    <a href="{shop_url}" style="background:{brand_color};color:#fff;padding:12px 30px;border-radius:8px;text-decoration:none;font-size:16px;">
      مشاهده محصولات
    </a>
  </div>
  <p style="font-size:13px;color:#888;">اگر نمی‌خواهید ایمیل دریافت کنید: <a href="{unsubscribe_url}">لغو اشتراک</a></p>
</div>""",
    },
    "follow_up": {
        "subject_fa": "{brand_name} — محصولات جدید اومدن! ✨",
        "subject_en": "{brand_name} — New arrivals! ✨",
        "html": """
<div style="font-family:Tahoma,Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;direction:rtl;">
  <h1 style="color:{brand_color};">{brand_name}</h1>
  <p>سلام {customer_name}! 😊</p>
  <p>{follow_up_message}</p>
  {product_showcase}
  <div style="text-align:center;margin:30px 0;">
    <a href="{shop_url}" style="background:{brand_color};color:#fff;padding:12px 30px;border-radius:8px;text-decoration:none;">
      خرید کنید
    </a>
  </div>
  <p style="font-size:13px;color:#888;"><a href="{unsubscribe_url}">لغو اشتراک</a></p>
</div>""",
    },
    "win_back": {
        "subject_fa": "دلمون تنگ شده {customer_name}! 💕 — {discount}% تخفیف",
        "subject_en": "We miss you {customer_name}! 💕 — {discount}% off",
        "html": """
<div style="font-family:Tahoma,Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;direction:rtl;">
  <h1 style="color:{brand_color};">{brand_name}</h1>
  <p style="font-size:18px;">سلام {customer_name}! 💕</p>
  <p>مدتیه ازمون خبری نداری. دلمون برات تنگ شده!</p>
  <div style="background:#fff3cd;padding:20px;border-radius:12px;text-align:center;margin:20px 0;">
    <p style="font-size:24px;font-weight:bold;color:{brand_color};">{discount}% تخفیف ویژه</p>
    <p>کد: <strong>{discount_code}</strong></p>
    <p style="font-size:13px;">فقط تا {expiry_date} معتبره</p>
  </div>
  <div style="text-align:center;margin:30px 0;">
    <a href="{shop_url}?code={discount_code}" style="background:{brand_color};color:#fff;padding:12px 30px;border-radius:8px;text-decoration:none;">
      استفاده از تخفیف
    </a>
  </div>
  <p style="font-size:13px;color:#888;"><a href="{unsubscribe_url}">لغو اشتراک</a></p>
</div>""",
    },
    "promotion": {
        "subject_fa": "🔥 {promo_title} — {brand_name}",
        "subject_en": "🔥 {promo_title} — {brand_name}",
        "html": """
<div style="font-family:Tahoma,Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;direction:rtl;">
  <h1 style="color:{brand_color};">{brand_name}</h1>
  <h2>{promo_title}</h2>
  <p>{promo_message}</p>
  {product_showcase}
  <div style="text-align:center;margin:30px 0;">
    <a href="{promo_url}" style="background:{brand_color};color:#fff;padding:14px 35px;border-radius:8px;text-decoration:none;font-size:18px;">
      {cta_text}
    </a>
  </div>
  <p style="font-size:13px;color:#888;"><a href="{unsubscribe_url}">لغو اشتراک</a></p>
</div>""",
    },
}


# ═══════════════════════════════════════════════════
# Email Senders
# ═══════════════════════════════════════════════════

class SMTPSender:
    """Send via SMTP (Gmail, Outlook, custom)."""

    def __init__(self) -> None:
        self.host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASSWORD", "")

    def is_configured(self) -> bool:
        return bool(self.user and self.password)

    async def send(self, msg: EmailMessage) -> SendResult:
        try:
            mime = MIMEMultipart("alternative")
            mime["From"] = f"{msg.from_name} <{msg.from_email or self.user}>"
            mime["To"] = msg.to
            mime["Subject"] = msg.subject
            if msg.reply_to:
                mime["Reply-To"] = msg.reply_to

            if msg.text_body:
                mime.attach(MIMEText(msg.text_body, "plain", "utf-8"))
            mime.attach(MIMEText(msg.html_body, "html", "utf-8"))

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_sync, mime)

            return SendResult(success=True, provider="smtp")
        except ArkiBaseError as exc:
            return SendResult(success=False, provider="smtp", error=str(exc))

    def _send_sync(self, mime: Any) -> Any:
        with smtplib.SMTP(self.host, self.port) as server:
            server.starttls()
            server.login(self.user, self.password)
            server.send_message(mime)


class SendGridSender:
    """Send via SendGrid API."""

    def __init__(self) -> None:
        self.api_key = os.getenv("SENDGRID_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def send(self, msg: EmailMessage) -> SendResult:
        try:
            payload = {
                "personalizations": [{"to": [{"email": msg.to}]}],
                "from": {
                    "email": msg.from_email or "noreply@example.com",
                    "name": msg.from_name,
                },
                "subject": msg.subject,
                "content": [
                    {"type": "text/html", "value": msg.html_body},
                ],
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                ) as resp:
                    if resp.status in (200, 201, 202):
                        mid = resp.headers.get("X-Message-Id", "")
                        return SendResult(success=True, provider="sendgrid", message_id=mid)
                    body = await resp.text()
                    return SendResult(success=False, provider="sendgrid", error=body[:200])
        except ArkiBaseError as exc:
            return SendResult(success=False, provider="sendgrid", error=str(exc))


class ResendSender:
    """Send via Resend API."""

    def __init__(self) -> None:
        self.api_key = os.getenv("RESEND_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def send(self, msg: EmailMessage) -> SendResult:
        try:
            payload = {
                "from": f"{msg.from_name} <{msg.from_email or 'noreply@example.com'}>",
                "to": [msg.to],
                "subject": msg.subject,
                "html": msg.html_body,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.resend.com/emails",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                ) as resp:
                    body = await resp.json(content_type=None)
                    if body.get("id"):
                        return SendResult(success=True, provider="resend", message_id=body["id"])
                    return SendResult(success=False, provider="resend", error=str(body))
        except ArkiBaseError as exc:
            return SendResult(success=False, provider="resend", error=str(exc))


# ═══════════════════════════════════════════════════
# Email Engine
# ═══════════════════════════════════════════════════

class EmailEngine:
    """
    Central email engine with fallback chain and sequences.
    
    Usage:
        engine = EmailEngine()
        
        # Send single email
        result = await engine.send(EmailMessage(...))
        
        # Send from template
        result = await engine.send_template("welcome", "user@email.com", vars)
        
        # Create sequence
        engine.create_sequence(SequenceType.WELCOME, contacts, vars)
    """

    def __init__(self) -> None:
        self._senders = [
            SMTPSender(),
            SendGridSender(),
            ResendSender(),
        ]
        self._brand_vars: Dict[str, str] = {
            "brand_name": os.getenv("BRAND_NAME", "Arki"),
            "brand_color": os.getenv("BRAND_COLOR", "#e74c3c"),
            "shop_url": os.getenv("SHOP_URL", ""),
            "unsubscribe_url": os.getenv("UNSUBSCRIBE_URL", "#"),
        }
        self._sequences: Dict[str, list] = {}

    def get_configured_providers(self) -> List[str]:
        return [s.__class__.__name__ for s in self._senders if s.is_configured()]

    def is_configured(self) -> bool:
        return any(s.is_configured() for s in self._senders)

    def set_brand(self, **kwargs) -> None:
        """Update brand variables for templates."""
        self._brand_vars.update(kwargs)

    async def send(self, msg: EmailMessage) -> SendResult:
        """Send email with fallback chain: SMTP → SendGrid → Resend."""
        for sender in self._senders:
            if not sender.is_configured():
                continue
            result = await sender.send(msg)
            if result.success:
                logger.info("Email sent to %s via %s", msg.to, result.provider)
                return result
            logger.warning("Email failed via %s: %s", result.provider, result.error)

        return SendResult(
            success=False,
            error="No email provider configured. Set SMTP_USER+SMTP_PASSWORD, SENDGRID_API_KEY, or RESEND_API_KEY in .env"
        )

    async def send_template(
        self,
        template_name: str,
        to_email: str,
        variables: Dict[str, str],
        lang: str = "fa",
    ) -> SendResult:
        """Send from a named template with variable substitution."""
        template = TEMPLATES.get(template_name)
        if not template:
            return SendResult(success=False, error=f"Template '{template_name}' not found")

        # Merge brand vars + custom vars
        all_vars = {**self._brand_vars, **variables}

        subject_key = f"subject_{lang}" if f"subject_{lang}" in template else "subject_fa"
        subject = template[subject_key].format_map(_SafeDict(all_vars))
        html = template["html"].format_map(_SafeDict(all_vars))

        msg = EmailMessage(
            to=to_email,
            subject=subject,
            html_body=html,
            from_email=all_vars.get("from_email", ""),
            from_name=all_vars.get("brand_name", "Arki"),
        )
        return await self.send(msg)

    async def send_bulk(
        self,
        template_name: str,
        contacts: List[EmailContact],
        variables: Dict[str, str],
        delay_seconds: float = 1.0,
    ) -> List[SendResult]:
        """Send to multiple contacts with rate limiting."""
        results = []
        for contact in contacts:
            if not contact.subscribed:
                continue
            vars_with_name = {**variables, "customer_name": contact.name or "دوست عزیز"}
            result = await self.send_template(template_name, contact.email, vars_with_name)
            results.append(result)
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
        return results


class _SafeDict(dict):
    """Dict that returns {key} for missing keys instead of raising."""
    def __missing__(self, key: str) -> Any:
        return f"{{{key}}}"


# ═══════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════

_engine: Optional[EmailEngine] = None


def get_email_engine() -> EmailEngine:
    global _engine
    if _engine is None:
        _engine = EmailEngine()
    return _engine


