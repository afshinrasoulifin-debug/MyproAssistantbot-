
"""Professional email templates for B2B outreach."""

TEMPLATES = {
    "nordic_b2b_intro": {
        "subject": "ArkiObjects — Handmade Concrete Décor for Your Space",
        "html": """
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Hello {prospect_name},</h2>
            <p>We create premium handmade concrete and stone candles for boutique hotels, 
            restaurants, and galleries across the Nordic region.</p>
            <p>Your {business_type} in {city} caught our attention — we think our collection 
            would be perfect for your aesthetic.</p>
            <p><a href="{cta_link}" style="background-color: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Our Catalog</a></p>
            <p>Best regards,<br>ArkiObjects Team</p>
        </div>
        """
    },
    "gallery_focus": {
        "subject": "Artisan Concrete Pieces for {gallery_name}",
        "html": """
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Hello {prospect_name},</h2>
            <p>We're reaching out because your gallery's aesthetic aligns perfectly with our 
            minimalist Scandinavian design philosophy.</p>
            <p>Our handmade concrete candles and stone accessories are unique, sustainable, 
            and highly sought after by collectors.</p>
            <p><a href="{cta_link}" style="background-color: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Schedule a Call</a></p>
            <p>Best regards,<br>ArkiObjects Team</p>
        </div>
        """
    },
    "followup_1": {
        "subject": "Re: ArkiObjects — Quick Question",
        "html": """
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <p>Hi {prospect_name},</p>
            <p>Just following up on our previous message. We'd love to discuss how our 
            products could enhance your space.</p>
            <p><a href="{cta_link}" style="background-color: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Let's Talk</a></p>
            <p>Best regards,<br>ArkiObjects Team</p>
        </div>
        """
    },
    "followup_2": {
        "subject": "Last Chance — Exclusive Preview",
        "html": """
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <p>Hi {prospect_name},</p>
            <p>We're launching a limited edition collection next month. We'd like to offer 
            you exclusive early access.</p>
            <p><a href="{cta_link}" style="background-color: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Claim Your Preview</a></p>
            <p>Best regards,<br>ArkiObjects Team</p>
        </div>
        """
    }
}

def get_template(template_name: str) -> dict:
    """Get email template by name."""
    return TEMPLATES.get(template_name, TEMPLATES["nordic_b2b_intro"])

def render_template(template_name: str, variables: dict) -> tuple:
    """Render template with variables."""
    template = get_template(template_name)
    subject = template["subject"].format(**variables)
    html = template["html"].format(**variables)
    return subject, html


