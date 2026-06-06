
from __future__ import annotations
"""
tg_bot/utils/integrations.py — External Service Integrations v9.3
Unified interface for external service connections.

Supports: Notion, Google Sheets, Airtable, Zapier, Slack, Discord,
          WhatsApp, Instagram, WooCommerce, HubSpot, Mailchimp
"""
import logging
import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════


logger = logging.getLogger(__name__)


@dataclass
class IntegrationConfig:
    name: str
    api_key: str = ""
    webhook_url: str = ""
    enabled: bool = False
    metadata: Dict[str, Any] = None


class IntegrationManager:
    """Manages all external integrations."""

    def __init__(self) -> None:
        self._integrations: Dict[str, IntegrationConfig] = {}
        self._auto_discover()

    def _auto_discover(self) -> Any:
        """Auto-discover configured integrations from environment."""
        env_map = {
            "notion": "NOTION_API_KEY",
            "google_sheets": "GOOGLE_SHEETS_KEY",
            "airtable": "AIRTABLE_API_KEY",
            "slack": "SLACK_BOT_TOKEN",
            "discord": "DISCORD_BOT_TOKEN",
            "whatsapp": "WHATSAPP_API_TOKEN",
            "instagram": "INSTAGRAM_ACCESS_TOKEN",
            "woocommerce": "WOOCOMMERCE_API_KEY",
            "shopify": "SHOPIFY_API_KEY",
            "hubspot": "HUBSPOT_API_KEY",
            "mailchimp": "MAILCHIMP_API_KEY",
            "sendgrid": "SENDGRID_API_KEY",
            "stripe": "STRIPE_SECRET_KEY",
            "zapier": "ZAPIER_WEBHOOK_URL",
        }
        for name, env_var in env_map.items():
            value = os.environ.get(env_var, "")
            if value:
                self._integrations[name] = IntegrationConfig(
                    name=name, api_key=value, enabled=True
                )
                logger.info("Integration discovered: %s", name)

    def get(self, name: str) -> Optional[IntegrationConfig]:
        return self._integrations.get(name)

    def is_enabled(self, name: str) -> bool:
        config = self._integrations.get(name)
        return config.enabled if config else False

    def list_enabled(self) -> List[str]:
        return [name for name, config in self._integrations.items() if config.enabled]

    # ── Notion ──
    async def notion_create_page(self, database_id: str, properties: Dict) -> Dict:
        config = self.get("notion")
        if not config:
            return {"error": "Notion not configured"}
        try:
            # v10.1: Route through TITANIUM
            if _TITANIUM_ACTIVE:
                resp = await shielded_post(
                    "https://api.notion.com/v1/pages",
                    json_data={"parent": {"database_id": database_id}, "properties": properties},
                    headers={"Authorization": f"Bearer {config.api_key}",
                             "Notion-Version": "2022-06-28"},
                    provider_name="notion",
                )
                return resp.json() if resp.success else {"error": f"HTTP {resp.status}"}
            else:
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "https://api.notion.com/v1/pages",
                        headers={"Authorization": f"Bearer {config.api_key}",
                                 "Notion-Version": "2022-06-28"},
                        json={"parent": {"database_id": database_id}, "properties": properties},
                    )
                    return resp.json()
        except Exception as e:
            return {"error": str(e)}

    # ── Google Sheets ──
    async def sheets_append(self, spreadsheet_id: str, range_: str, values: List[List]) -> Dict:
        config = self.get("google_sheets")
        if not config:
            return {"error": "Google Sheets not configured"}
        # Uses service account JSON key
        return {"status": "configured", "note": "Requires gspread library"}

    # ── Zapier/Make Webhook ──
    async def trigger_webhook(self, name: str, data: Dict) -> bool:
        config = self.get(name)
        if not config or not config.webhook_url:
            return False
        try:
            # v10.1: Route through TITANIUM
            if _TITANIUM_ACTIVE:
                resp = await shielded_post(
                    config.webhook_url, json_data=data,
                    timeout=10.0, provider_name=f"webhook:{name}",
                )
                return resp.success
            else:
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.post(config.webhook_url, json=data, timeout=10)
                    return resp.status_code == 200
        except Exception as e:
            logger.error("Webhook %s failed: %s", name, e)
            return False

    # ── CRM (HubSpot) ──
    async def crm_create_contact(self, email: str, name: str, properties: Dict = None) -> Dict:
        config = self.get("hubspot")
        if not config:
            return {"error": "HubSpot not configured"}
        try:
            # v10.1: Route through TITANIUM
            if _TITANIUM_ACTIVE:
                resp = await shielded_post(
                    "https://api.hubapi.com/crm/v3/objects/contacts",
                    json_data={"properties": {"email": email, "firstname": name, **(properties or {})}},
                    headers={"Authorization": f"Bearer {config.api_key}"},
                    provider_name="hubspot",
                )
                return resp.json() if resp.success else {"error": f"HTTP {resp.status}"}
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.hubapi.com/crm/v3/objects/contacts",
                    headers={"Authorization": f"Bearer {config.api_key}"},
                    json={"properties": {"email": email, "firstname": name, **(properties or {})}},
                )
                return resp.json()
        except Exception as e:
            return {"error": str(e)}

    @property
    def stats(self) -> dict:
        return {
            "total": len(self._integrations),
            "enabled": len(self.list_enabled()),
            "services": self.list_enabled(),
        }


_manager: Optional[IntegrationManager] = None

def get_integration_manager() -> IntegrationManager:
    global _manager
    if _manager is None:
        _manager = IntegrationManager()
    return _manager


