
from __future__ import annotations
"""
tg_bot/utils/outreach_engine.py — Marketing Agent TITAN (L9)
═════════════════════════════════════════════════════════════
AI-powered multi-language email outreach engine with A/B testing.

Architecture
────────────
   ┌─────────────────────────────────────────────────────────┐
   │                   OUTREACH ENGINE                        │
   ├──────────┬──────────┬──────────┬──────────┬─────────────┤
   │ Content  │ Sequence │ Send     │ Track    │ Learn       │
   ├──────────┼──────────┼──────────┼──────────┼─────────────┤
   │ AI Gen   │ 4-Step   │ Timezone │ Opens    │ A/B Test    │
   │ Native   │ Intro    │ Queue    │ Clicks   │ Winner      │
   │ Language │ Follow   │ Throttle │ Replies  │ Optimize    │
   │ Personal │ Catalog  │ Provider │ Bounce   │ Improve     │
   │ Catalog  │ Offer    │ Retry    │ Unsub    │ Report      │
   └──────────┴──────────┴──────────┴──────────┴─────────────┘

4-Step Outreach Sequence
────────────────────────
  Step 0 (Day 0):   Introduction — product highlights, brand story
  Step 1 (Day 3):   Follow-up — social proof, customer testimonials
  Step 2 (Day 7):   Catalog — PDF attachment with full product range
  Step 3 (Day 14):  Special offer — limited discount, urgency

Reuses
──────
  • email_engine.py — SMTP / SendGrid / Resend delivery
  • marketing_engine.py — A/B testing framework
  • ai_client.py — AI content generation
"""


import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ── Existing modules ──
try:
    from arki_project.utils.email_engine import EmailEngine
    _EMAIL_ENGINE_AVAILABLE = True
except ImportError:
    _EMAIL_ENGINE_AVAILABLE = False

try:
    from arki_project.utils.ai_client import AIClient
    _AI_CLIENT_AVAILABLE = True
except ImportError:
    _AI_CLIENT_AVAILABLE = False

# ── OMEGA modules ──
try:
    from arki_project.utils.content_forge_engine import ContentForgeEngine, ContentLanguage, ContentType
    _CONTENT_FORGE_AVAILABLE = True
except ImportError:
    _CONTENT_FORGE_AVAILABLE = False

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Language Templates
# ═══════════════════════════════════════════════════════════

LANGUAGE_GREETINGS = {
    "en": {"greeting": "Dear", "regards": "Best regards", "company_intro": "We are ArkiObjects, a Finnish handmade candle and stone accessories brand."},
    "fi": {"greeting": "Hyvä", "regards": "Ystävällisin terveisin", "company_intro": "Olemme ArkiObjects, suomalainen käsintehtyjen betoni- ja kynttilätuotteiden brändi."},
    "sv": {"greeting": "Kära", "regards": "Med vänliga hälsningar", "company_intro": "Vi är ArkiObjects, ett finskt varumärke för handgjorda ljus och stenaccessoarer."},
    "de": {"greeting": "Sehr geehrte/r", "regards": "Mit freundlichen Grüßen", "company_intro": "Wir sind ArkiObjects, eine finnische Marke für handgefertigte Betonkerzen und Steinaccessoires."},
    "fr": {"greeting": "Cher/Chère", "regards": "Cordialement", "company_intro": "Nous sommes ArkiObjects, une marque finlandaise de bougies artisanales en béton et d'accessoires en pierre."},
    "no": {"greeting": "Kjære", "regards": "Med vennlig hilsen", "company_intro": "Vi er ArkiObjects, et finsk merke for håndlagde betongstearinlys og steintilbehør."},
    "da": {"greeting": "Kære", "regards": "Med venlig hilsen", "company_intro": "Vi er ArkiObjects, et finsk brand for håndlavede betonlys og stentilbehør."},
    "nl": {"greeting": "Geachte", "regards": "Met vriendelijke groet", "company_intro": "Wij zijn ArkiObjects, een Fins merk voor handgemaakte betonnen kaarsen en stenen accessoires."},
}

# ═══════════════════════════════════════════════════════════
# Sequence Templates (Step definitions)
# ═══════════════════════════════════════════════════════════

DEFAULT_SEQUENCE = [
    {
        "step": 0,
        "delay_days": 0,
        "name": "introduction",
        "subject_hint": "Unique handmade décor from Finland for {business_name}",
        "content_focus": "introduction, brand story, product highlights, Scandinavian minimalism",
        "attach_catalog": False,
    },
    {
        "step": 1,
        "delay_days": 3,
        "name": "followup",
        "subject_hint": "Following up — ArkiObjects × {business_name}",
        "content_focus": "social proof, customer testimonials, Instagram highlights, product in context",
        "attach_catalog": False,
    },
    {
        "step": 2,
        "delay_days": 7,
        "name": "catalog",
        "subject_hint": "Our full collection for {business_name}",
        "content_focus": "full product range, wholesale pricing, custom options, catalog attached",
        "attach_catalog": True,
    },
    {
        "step": 3,
        "delay_days": 14,
        "name": "special_offer",
        "subject_hint": "Special offer for {business_name} — limited availability",
        "content_focus": "limited discount, urgency, seasonal tie-in, clear CTA",
        "attach_catalog": False,
    },
]


@dataclass
class EmailContent:
    """Generated email content ready for sending."""
    subject: str = ""
    body_html: str = ""
    body_text: str = ""
    language: str = "en"
    variant_label: Optional[str] = None


@dataclass
class OutreachResult:
    """Result of an outreach operation."""
    emails_generated: int = 0
    emails_queued: int = 0
    emails_sent: int = 0
    emails_failed: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "emails_generated": self.emails_generated,
            "emails_queued": self.emails_queued,
            "emails_sent": self.emails_sent,
            "emails_failed": self.emails_failed,
            "errors": self.errors,
            "duration_seconds": round(self.duration_seconds, 1),
        }


# ═══════════════════════════════════════════════════════════
# Outreach Engine
# ═══════════════════════════════════════════════════════════

class OutreachEngine:
    """
    AI-powered multi-language email outreach engine.

    Provides:
    - AI email content generation in target language
    - 4-step automated sequence management
    - A/B testing on subject lines and body content
    - Timezone-aware sending schedule
    - Catalog PDF attachment
    - Delivery tracking integration
    """

    def __init__(
        self,
        *,
        daily_limit: int = 50,
        from_email: str = "hello@arkiobjects.com",
        from_name: str = "ArkiObjects Finland",
        catalog_pdf_path: str = "assets/catalog.pdf",
        ai_client: Optional[Any] = None,
    ) -> None:
        self._daily_limit = daily_limit
        self._from_email = from_email
        self._from_name = from_name
        self._catalog_path = catalog_pdf_path
        self._ai_client = ai_client
        self._emails_sent_today = 0
        self._today_date: Optional[str] = None
        self._email_engine = EmailEngine() if _EMAIL_ENGINE_AVAILABLE else None
        # OMEGA content forge for advanced email generation
        self._content_forge = ContentForgeEngine(ai_client=ai_client) if _CONTENT_FORGE_AVAILABLE else None

    # ── Campaign Execution ───────────────────────────────

    async def execute_campaign_step(
        self,
        campaign_id: int,
        step_number: int,
        prospects: List[Dict[str, Any]],
        *,
        data_bridge=None,
        ab_test: bool = False,
    ) -> OutreachResult:
        """
        Execute a single step of a campaign for a list of prospects.

        Generates personalised emails, optionally with A/B variants,
        queues them, and sends within the daily limit.
        """
        start = time.monotonic()
        result = OutreachResult()

        step = DEFAULT_SEQUENCE[step_number] if step_number < len(DEFAULT_SEQUENCE) else DEFAULT_SEQUENCE[0]

        for prospect in prospects:
            if self._daily_limit_reached():
                result.errors.append("Daily email limit reached")
                break

            # Skip opted-out prospects
            if prospect.get("opted_out"):
                continue

            # Skip prospects without email
            if not prospect.get("email"):
                continue

            try:
                # Generate email content
                language = prospect.get("language", "en")
                
                # OMEGA: Fetch recon report if available
                recon_report = None
                if data_bridge and hasattr(data_bridge, "get_recon_report"):
                    recon_data = await data_bridge.get_recon_report(prospect["id"])
                    if recon_data:
                        from arki_project.utils.deep_recon_engine import DeepReconReport
                        recon_report = DeepReconReport.from_dict(recon_data)

                content = await self.generate_email(
                    prospect=prospect,
                    step=step,
                    language=language,
                    recon_report=recon_report,
                    personalizer=getattr(self, "_personalizer", None)
                )
                result.emails_generated += 1

                # A/B variant
                if ab_test:
                    content_b = await self.generate_email(
                        prospect=prospect,
                        step=step,
                        language=language,
                        variant="B",
                        recon_report=recon_report,
                        personalizer=getattr(self, "_personalizer", None)
                    )
                    # Randomly assign variant (simple 50/50 split)
                    import random
                    chosen = content if random.random() < 0.5 else content_b
                    chosen.variant_label = "A" if chosen is content else "B"
                    content = chosen

                # Queue in data bridge
                if data_bridge:
                    email_id = await data_bridge.queue_email({
                        "campaign_id": campaign_id,
                        "prospect_id": prospect["id"],
                        "sequence_step": step_number,
                        "to_email": prospect["email"],
                        "subject": content.subject,
                        "body_html": content.body_html,
                        "language": content.language,
                        "variant_label": content.variant_label,
                    })
                    if email_id:
                        result.emails_queued += 1

                # Send immediately
                sent = await self._send_email(
                    to_email=prospect["email"],
                    subject=content.subject,
                    body_html=content.body_html,
                    attach_catalog=step.get("attach_catalog", False),
                )

                if sent:
                    result.emails_sent += 1
                    self._emails_sent_today += 1

                    if data_bridge:
                        await data_bridge.update_email_status(
                            email_id, "sent",
                            sent_at=datetime.now(timezone.utc),
                            provider=self._get_provider_name(),
                        )
                        await data_bridge.log_event(
                            "email_sent",
                            prospect_id=prospect["id"],
                            campaign_id=campaign_id,
                            email_id=email_id,
                            outcome="success",
                        )
                        # Update prospect status
                        if prospect.get("status") == "qualified":
                            await data_bridge.update_prospect(
                                prospect["id"],
                                {"status": "contacted", "last_contacted_at": datetime.now(timezone.utc)},
                            )
                else:
                    result.emails_failed += 1

            except Exception as exc:
                result.errors.append(f"Prospect {prospect.get('id')}: {exc}")
                result.emails_failed += 1

            # Throttle: small delay between emails
            await asyncio.sleep(3.0)

        result.duration_seconds = time.monotonic() - start
        return result

    # ── Email Content Generation ─────────────────────────

    async def generate_email(
        self,
        *,
        prospect: Dict[str, Any],
        step: Dict[str, Any],
        language: str = "en",
        variant: Optional[str] = None,
        recon_report: Optional[Any] = None,
        personalizer: Optional[Any] = None,
    ) -> EmailContent:
        """
        Generate a personalised email using AI in the target language.

        Falls back to template-based generation if AI is unavailable.
        """
        # TITANIUM v30: Advanced AI Personalization
        if _AI_CLIENT_AVAILABLE:
            try:
                from arki_project.utils.ai_marketing_intelligence import AIMarketingIntelligence
                ai_intel = AIMarketingIntelligence(self._ai_client or AIClient())
                
                context = {
                    "prospect": prospect,
                    "step": step,
                    "recon_report": recon_report.to_dict() if recon_report else None,
                    "variant": variant
                }
                
                optimized_body = await ai_intel.optimize_content_for_persona(
                    content=f"Step {step.get('step')} marketing outreach",
                    persona=context
                )
                
                return EmailContent(
                    subject=step.get("subject_hint", "Hello").format(business_name=prospect.get("business_name", "there")),
                    body_html=optimized_body,
                    body_text=optimized_body, # Simplified for now
                    language=language,
                    variant_label=variant
                )
            except Exception as e:
                logger.error(f"AI personalization failed, falling back to templates: {e}")

        lang_data = LANGUAGE_GREETINGS.get(language, LANGUAGE_GREETINGS["en"])

        business_name = prospect.get("business_name", "your business")
        contact_name = prospect.get("contact_person", "")
        business_type = prospect.get("business_type", "business")
        city = prospect.get("city", "")
        country = prospect.get("country", "")

        # Build subject
        subject_hint = step.get("subject_hint", "ArkiObjects — Handmade Décor from Finland")
        subject = subject_hint.format(business_name=business_name)

        if variant == "B":
            # A/B variant: different subject angle
            subject = f"Handmade Finnish décor — perfect for {business_name}"

        # ── OMEGA: Try ContentForge first ────────────────
        if self._content_forge:
            try:
                lang_map = {
                    "en": ContentLanguage.EN, "fi": ContentLanguage.FI,
                    "sv": ContentLanguage.SV, "de": ContentLanguage.DE,
                    "fr": ContentLanguage.FR,
                }
                forge_lang = lang_map.get(language, ContentLanguage.EN)
                industry = prospect.get("business_type", "generic")
                followup = step.get("step_number", 1) - 1
                forge_result = await self._content_forge.generate_b2b_email(
                    prospect={
                        "name": contact_name or "Sir/Madam",
                        "company": business_name,
                        "title": prospect.get("contact_role", ""),
                        "domain": prospect.get("website", ""),
                    },
                    language=forge_lang,
                    industry=industry,
                    followup_number=followup,
                    sender_name=self._from_name,
                )
                # Validate brand voice
                validation = self._content_forge.validate_brand_voice(forge_result.body)
                if validation.get("valid", True):
                    body = forge_result.body
                    # OMEGA Hyper-Personalization
                    if recon_report and personalizer:
                        body = await personalizer.craft_personalized_email(
                            prospect=prospect,
                            recon_report=recon_report,
                            base_content=body,
                            language=language
                        )

                    return EmailContent(
                        subject=forge_result.subject or subject,
                        body_html=body,
                        language=language,
                        variant_label=variant,
                    )
                else:
                    logger.debug("ContentForge output failed brand check: %s", validation.get("issues"))
            except Exception as exc:
                logger.debug("ContentForge email gen failed: %s", exc)

        # Try AI generation
        if self._ai_client:
            try:
                body_html = await self._generate_with_ai(
                    prospect=prospect,
                    step=step,
                    language=language,
                    lang_data=lang_data,
                    variant=variant,
                )
                return EmailContent(
                    subject=subject,
                    body_html=body_html,
                    language=language,
                    variant_label=variant,
                )
            except Exception as exc:
                logger.warning("AI email generation failed, using template: %s", exc)

        # Fallback: template-based
        body_html = self._generate_template_email(
            prospect=prospect,
            step=step,
            language=language,
            lang_data=lang_data,
        )

        return EmailContent(
            subject=subject,
            body_html=body_html,
            language=language,
            variant_label=variant,
        )

    async def _generate_with_ai(
        self,
        *,
        prospect: Dict[str, Any],
        step: Dict[str, Any],
        language: str,
        lang_data: Dict[str, str],
        variant: Optional[str] = None,
    ) -> str:
        """Generate email body using the AI client."""
        prompt = f"""Generate a professional B2B outreach email with these parameters:

LANGUAGE: {language} (write the ENTIRE email in this language)
STEP: {step.get('name', 'introduction')} (step {step.get('step', 0)} of 4)
FOCUS: {step.get('content_focus', 'introduction')}

SENDER:
- Brand: ArkiObjects (Finnish handmade concrete candles & stone accessories)
- Style: Minimalist Scandinavian
- Location: Pieksämäki, Finland
- Price range: €10-50

RECIPIENT:
- Business: {prospect.get('business_name', 'Unknown')}
- Type: {prospect.get('business_type', 'business')}
- Contact: {prospect.get('contact_person', '')}
- Role: {prospect.get('contact_role', '')}
- City: {prospect.get('city', '')}, {prospect.get('country', '')}

{'VARIANT B: Use a different angle and tone.' if variant == 'B' else ''}

Requirements:
1. Professional but warm tone
2. Personalised to the recipient's business type
3. Explain why our products fit their space
4. Include a clear call-to-action
5. Keep it concise (150-250 words)
6. Format as clean HTML with minimal styling
7. Include unsubscribe note at bottom (GDPR)

Return ONLY the HTML email body, no subject line."""

        response = await self._ai_client.generate(prompt)
        if isinstance(response, dict):
            return response.get("text", response.get("content", ""))
        return str(response) if response else ""

    def _generate_template_email(
        self,
        *,
        prospect: Dict[str, Any],
        step: Dict[str, Any],
        language: str,
        lang_data: Dict[str, str],
    ) -> str:
        """Generate a template-based email (fallback when AI is unavailable)."""
        greeting = lang_data.get("greeting", "Dear")
        regards = lang_data.get("regards", "Best regards")
        intro = lang_data.get("company_intro", "We are ArkiObjects from Finland.")

        contact = prospect.get("contact_person", "")
        business = prospect.get("business_name", "your business")
        btype = prospect.get("business_type", "business")

        salutation = f"{greeting} {contact}," if contact else f"{greeting} {business} team,"

        step_name = step.get("name", "introduction")

        if step_name == "introduction":
            body = f"""<p>{salutation}</p>
<p>{intro}</p>
<p>Our handcrafted concrete candles and stone accessories bring a unique Scandinavian touch
to any space. We believe they would be a wonderful addition to {business}.</p>
<p>Each piece is individually hand-poured in our Pieksämäki studio, making every item
truly one-of-a-kind. Prices range from €10-50, perfect for retail or decoration.</p>
<p>Would you be open to a brief conversation about how we could collaborate?</p>"""

        elif step_name == "followup":
            body = f"""<p>{salutation}</p>
<p>I wanted to follow up on my previous email about ArkiObjects handmade products.</p>
<p>Our products are featured in several {btype}s across the Nordics, and we've received
wonderful feedback about how they enhance the ambiance of any space.</p>
<p>Would you like to see some examples of how our pieces look in similar settings?</p>"""

        elif step_name == "catalog":
            body = f"""<p>{salutation}</p>
<p>I'd love to share our complete product catalog with you.
Attached you'll find our current collection with wholesale pricing options.</p>
<p>Highlights include our signature concrete tealight holders, geometric candle sets,
and our new stone accessories line — all handmade in Finland.</p>
<p>We offer flexible ordering and shipping across Europe. Would any of these
be a fit for {business}?</p>"""

        else:  # special_offer
            body = f"""<p>{salutation}</p>
<p>As we prepare for the upcoming season, I wanted to extend a special offer
exclusively for {business}.</p>
<p>For first-time wholesale orders, we're offering 15% off our standard pricing,
plus free shipping within the EU.</p>
<p>This offer is available for a limited time. Shall I put together a custom
selection for your space?</p>"""

        footer = f"""<p>{regards},<br>ArkiObjects Finland<br>
<em>Handmade Concrete & Stone Candles</em><br>
Pieksämäki, Finland</p>
<p style="font-size:11px;color:#999;">If you prefer not to receive these emails,
please reply with "unsubscribe" and we'll remove you immediately.</p>"""

        return f"<div>{body}{footer}</div>"

    # ── Email Sending ────────────────────────────────────

    async def _send_email(
        self,
        *,
        to_email: str,
        subject: str,
        body_html: str,
        attach_catalog: bool = False,
    ) -> bool:
        """Send an email via the email engine."""
        if not self._email_engine:
            logger.warning("EmailEngine not available, email queued but not sent")
            return False

        try:
            attachments = []
            if attach_catalog:
                import os
                if os.path.exists(self._catalog_path):
                    attachments.append(self._catalog_path)

            result = await self._email_engine.send(
                to=to_email,
                subject=subject,
                body_html=body_html,
                from_email=self._from_email,
                from_name=self._from_name,
                attachments=attachments,
            )
            return bool(result)

        except Exception as exc:
            logger.error("Email send failed to %s: %s", to_email, exc)
            return False

    # ── Sequence Management ──────────────────────────────

    async def get_due_followups(
        self,
        campaign_id: int,
        *,
        data_bridge=None,
    ) -> List[Dict[str, Any]]:
        """
        Find prospects due for the next follow-up in a campaign.

        Checks the last email sent to each prospect and determines
        if enough days have passed for the next sequence step.
        """
        if not data_bridge:
            return []

        # Get campaign details
        campaign = await data_bridge.get_campaign(campaign_id)
        if not campaign or campaign["status"] != "active":
            return []

        # Get all emails for this campaign, grouped by prospect
        # This would be a more complex query in production
        due_followups = []

        # Get prospects contacted in this campaign
        prospects = await data_bridge.get_prospects(
            status="contacted",
            limit=200,
        )

        now = datetime.now(timezone.utc)
        for prospect in prospects:
            last_contact = prospect.get("last_contacted_at")
            if not last_contact:
                continue

            # Determine which step they're on and if next is due
            # (simplified — production would track per-prospect sequence state)
            try:
                if isinstance(last_contact, str):
                    last_dt = datetime.fromisoformat(last_contact.replace("Z", "+00:00"))
                else:
                    last_dt = last_contact

                days_since = (now - last_dt).days

                # Check against sequence delays
                for step in DEFAULT_SEQUENCE[1:]:  # Skip step 0 (already sent)
                    if days_since >= step["delay_days"]:
                        due_followups.append({
                            "prospect": prospect,
                            "next_step": step["step"],
                            "days_since_last": days_since,
                        })
                        break  # Only next step

            except Exception:
                continue

        return due_followups

    # ── Helpers ──────────────────────────────────────────

    def _daily_limit_reached(self) -> bool:
        """Check if daily email limit has been reached."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._today_date != today:
            self._today_date = today
            self._emails_sent_today = 0
        return self._emails_sent_today >= self._daily_limit

    def _get_provider_name(self) -> str:
        """Get the name of the active email provider."""
        if self._email_engine:
            return getattr(self._email_engine, "provider", "smtp")
        return "none"

    def get_stats(self) -> Dict[str, Any]:
        """Get outreach engine statistics."""
        return {
            "emails_sent_today": self._emails_sent_today,
            "daily_limit": self._daily_limit,
            "email_engine_available": _EMAIL_ENGINE_AVAILABLE,
            "ai_client_available": self._ai_client is not None,
            "from_email": self._from_email,
            "sequence_steps": len(DEFAULT_SEQUENCE),
        }


