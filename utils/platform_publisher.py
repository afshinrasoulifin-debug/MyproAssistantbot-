
from __future__ import annotations
from arki_project.exceptions import PlatformError
"""
tg_bot/utils/platform_publisher.py — Real Platform Publishing Engine v1.0
═══════════════════════════════════════════════════════════════════════════
Actually posts content to platforms via their APIs.

Supported:
  • Telegram Channel  — Bot API (free, no limit)
  • Instagram         — Graph API (Business/Creator account)
  • Etsy              — Open API v3
  • Shopify           — Admin API
  • WooCommerce       — REST API
  • WordPress         — REST API

Each publisher is independent and gracefully degrades if API keys are missing.
"""


import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

# ── TITANIUM Integration ──
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False

try:
    from arki_project.utils.http_pool import get_client
except ImportError:
    get_client = None

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════

class PlatformType(str, Enum):
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"
    ETSY = "etsy"
    SHOPIFY = "shopify"
    WOOCOMMERCE = "woocommerce"
    WORDPRESS = "wordpress"


@dataclass
class PublishResult:
    platform: PlatformType
    success: bool
    post_id: str = ""
    post_url: str = ""
    error: str = ""
    latency_ms: float = 0.0


@dataclass
class ContentPayload:
    """Universal content structure for all platforms."""
    title: str = ""
    body: str = ""
    caption: str = ""
    hashtags: List[str] = field(default_factory=list)
    image_urls: List[str] = field(default_factory=list)
    image_paths: List[str] = field(default_factory=list)
    price: float = 0.0
    currency: str = "EUR"
    category: str = ""
    tags: List[str] = field(default_factory=list)
    platform_specific: Dict[str, Any] = field(default_factory=dict)

    @property
    def full_caption(self) -> str:
        parts = [self.caption]
        if self.hashtags:
            parts.append(" ".join(f"#{h.strip('#')}" for h in self.hashtags))
        return "\n\n".join(p for p in parts if p)


# ═══════════════════════════════════════════════════
# Base Publisher
# ═══════════════════════════════════════════════════

class BasePublisher:
    """Base class for all platform publishers."""
    platform: PlatformType = PlatformType.TELEGRAM

    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60)
            )
        return self._session

    async def close(self) -> Any:
        if self._session and not self._session.closed:
            await self._session.close()

    def is_configured(self) -> bool:
        """Override: return True if API keys are present."""
        return False

    async def publish(self, content: ContentPayload) -> PublishResult:
        """Override: publish content to the platform."""
        return PublishResult(
            platform=self.platform, success=False,
            error="Not implemented"
        )

    async def _safe_request(
        self, method: str, url: str,
        headers: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        data: Optional[Any] = None,
    ) -> Tuple[int, Dict]:
        """HTTP request with error handling."""
        t0 = time.monotonic()
        try:
            if _TITANIUM_ACTIVE:
                resp = await shielded_request(
                    method, url, headers=headers,
                    json_body=json_data, data=data,
                )
                return resp.status, json.loads(resp.text) if resp.text else {}

            session = await self._get_session()
            async with session.request(
                method, url, headers=headers,
                json=json_data, data=data,
            ) as resp:
                body = await resp.json(content_type=None)
                return resp.status, body or {}
        except PlatformError as exc:
            logger.error("[%s] request error: %s", self.platform.value, exc)
            return 0, {"error": str(exc)}


# ═══════════════════════════════════════════════════
# Telegram Channel Publisher
# ═══════════════════════════════════════════════════

class TelegramPublisher(BasePublisher):
    """Post to Telegram channel via Bot API."""
    platform = PlatformType.TELEGRAM

    def __init__(self) -> None:
        super().__init__()
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.channel_ids = [
            c.strip() for c in
            os.getenv("TELEGRAM_CHANNEL_IDS", "").split(",") if c.strip()
        ]

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.channel_ids)

    async def publish(self, content: ContentPayload) -> PublishResult:
        if not self.is_configured():
            return PublishResult(
                platform=self.platform, success=False,
                error="TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_IDS not set"
            )

        t0 = time.monotonic()
        base = f"https://api.telegram.org/bot{self.bot_token}"
        results = []

        for ch_id in self.channel_ids:
            try:
                if content.image_urls:
                    # Send photo with caption
                    status, body = await self._safe_request(
                        "POST", f"{base}/sendPhoto",
                        json_data={
                            "chat_id": ch_id,
                            "photo": content.image_urls[0],
                            "caption": content.full_caption[:1024],
                            "parse_mode": "HTML",
                        }
                    )
                else:
                    status, body = await self._safe_request(
                        "POST", f"{base}/sendMessage",
                        json_data={
                            "chat_id": ch_id,
                            "text": content.full_caption[:4096],
                            "parse_mode": "HTML",
                        }
                    )

                if body.get("ok"):
                    msg_id = body["result"]["message_id"]
                    results.append(PublishResult(
                        platform=self.platform, success=True,
                        post_id=str(msg_id),
                        post_url=f"https://t.me/c/{ch_id}/{msg_id}",
                        latency_ms=(time.monotonic() - t0) * 1000,
                    ))
                else:
                    results.append(PublishResult(
                        platform=self.platform, success=False,
                        error=body.get("description", "Unknown error"),
                    ))
            except PlatformError as exc:
                results.append(PublishResult(
                    platform=self.platform, success=False,
                    error=str(exc),
                ))

        # Return first success or first error
        for r in results:
            if r.success:
                return r
        return results[0] if results else PublishResult(
            platform=self.platform, success=False, error="No channels"
        )


# ═══════════════════════════════════════════════════
# Instagram Graph API Publisher
# ═══════════════════════════════════════════════════

class InstagramPublisher(BasePublisher):
    """Post to Instagram via Graph API (Business/Creator account required)."""
    platform = PlatformType.INSTAGRAM

    def __init__(self) -> None:
        super().__init__()
        self.access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
        self.account_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")

    def is_configured(self) -> bool:
        return bool(self.access_token and self.account_id)

    async def publish(self, content: ContentPayload) -> PublishResult:
        if not self.is_configured():
            return PublishResult(
                platform=self.platform, success=False,
                error="INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_BUSINESS_ACCOUNT_ID not set"
            )

        t0 = time.monotonic()
        base = "https://graph.facebook.com/v19.0"

        try:
            # Step 1: Create media container
            if len(content.image_urls) > 1:
                # Carousel
                children = []
                for img_url in content.image_urls[:10]:
                    status, body = await self._safe_request(
                        "POST", f"{base}/{self.account_id}/media",
                        json_data={
                            "image_url": img_url,
                            "is_carousel_item": True,
                            "access_token": self.access_token,
                        }
                    )
                    if body.get("id"):
                        children.append(body["id"])

                status, body = await self._safe_request(
                    "POST", f"{base}/{self.account_id}/media",
                    json_data={
                        "media_type": "CAROUSEL",
                        "children": ",".join(children),
                        "caption": content.full_caption[:2200],
                        "access_token": self.access_token,
                    }
                )
            elif content.image_urls:
                # Single image
                status, body = await self._safe_request(
                    "POST", f"{base}/{self.account_id}/media",
                    json_data={
                        "image_url": content.image_urls[0],
                        "caption": content.full_caption[:2200],
                        "access_token": self.access_token,
                    }
                )
            else:
                return PublishResult(
                    platform=self.platform, success=False,
                    error="Instagram requires at least one image"
                )

            container_id = body.get("id")
            if not container_id:
                return PublishResult(
                    platform=self.platform, success=False,
                    error=body.get("error", {}).get("message", "Failed to create container"),
                )

            # Step 2: Wait for processing
            await asyncio.sleep(5)

            # Step 3: Publish
            status, body = await self._safe_request(
                "POST", f"{base}/{self.account_id}/media_publish",
                json_data={
                    "creation_id": container_id,
                    "access_token": self.access_token,
                }
            )

            if body.get("id"):
                return PublishResult(
                    platform=self.platform, success=True,
                    post_id=body["id"],
                    post_url=f"https://www.instagram.com/p/{body['id']}/",
                    latency_ms=(time.monotonic() - t0) * 1000,
                )
            else:
                return PublishResult(
                    platform=self.platform, success=False,
                    error=body.get("error", {}).get("message", "Publish failed"),
                )

        except PlatformError as exc:
            return PublishResult(
                platform=self.platform, success=False,
                error=str(exc),
            )


# ═══════════════════════════════════════════════════
# Etsy Open API v3 Publisher
# ═══════════════════════════════════════════════════

class EtsyPublisher(BasePublisher):
    """Create/update Etsy listings via Open API v3."""
    platform = PlatformType.ETSY

    def __init__(self) -> None:
        super().__init__()
        self.api_key = os.getenv("ETSY_API_KEY", "")
        self.access_token = os.getenv("ETSY_ACCESS_TOKEN", "")
        self.shop_id = os.getenv("ETSY_SHOP_ID", "")

    def is_configured(self) -> bool:
        return bool(self.api_key and self.access_token and self.shop_id)

    async def publish(self, content: ContentPayload) -> PublishResult:
        if not self.is_configured():
            return PublishResult(
                platform=self.platform, success=False,
                error="ETSY_API_KEY, ETSY_ACCESS_TOKEN, or ETSY_SHOP_ID not set"
            )

        t0 = time.monotonic()
        base = "https://openapi.etsy.com/v3"

        try:
            tags = (content.tags or content.hashtags)[:13]  # Etsy max 13 tags

            listing_data = {
                "title": content.title[:140],
                "description": content.body or content.caption,
                "price": content.price or 1.0,
                "who_made": "i_did",
                "when_made": "made_to_order",
                "taxonomy_id": content.platform_specific.get("etsy_taxonomy_id", 0),
                "tags": tags,
                "quantity": content.platform_specific.get("quantity", 999),
            }

            status, body = await self._safe_request(
                "POST",
                f"{base}/application/shops/{self.shop_id}/listings",
                headers={
                    "x-api-key": self.api_key,
                    "Authorization": f"Bearer {self.access_token}",
                },
                json_data=listing_data,
            )

            if body.get("listing_id"):
                lid = body["listing_id"]
                return PublishResult(
                    platform=self.platform, success=True,
                    post_id=str(lid),
                    post_url=f"https://www.etsy.com/listing/{lid}",
                    latency_ms=(time.monotonic() - t0) * 1000,
                )
            else:
                return PublishResult(
                    platform=self.platform, success=False,
                    error=body.get("error", "Failed to create listing"),
                )

        except PlatformError as exc:
            return PublishResult(
                platform=self.platform, success=False,
                error=str(exc),
            )


# ═══════════════════════════════════════════════════
# Shopify Admin API Publisher
# ═══════════════════════════════════════════════════

class ShopifyPublisher(BasePublisher):
    """Create products on Shopify via Admin API."""
    platform = PlatformType.SHOPIFY

    def __init__(self) -> None:
        super().__init__()
        self.store_url = os.getenv("SHOPIFY_STORE_URL", "").rstrip("/")
        self.access_token = os.getenv("SHOPIFY_ACCESS_TOKEN", "")

    def is_configured(self) -> bool:
        return bool(self.store_url and self.access_token)

    async def publish(self, content: ContentPayload) -> PublishResult:
        if not self.is_configured():
            return PublishResult(
                platform=self.platform, success=False,
                error="SHOPIFY_STORE_URL or SHOPIFY_ACCESS_TOKEN not set"
            )

        t0 = time.monotonic()

        try:
            images = [{"src": u} for u in content.image_urls[:10]]
            product_data = {
                "product": {
                    "title": content.title,
                    "body_html": f"<p>{content.body or content.caption}</p>",
                    "vendor": content.platform_specific.get("vendor", ""),
                    "product_type": content.category,
                    "tags": ", ".join(content.tags or content.hashtags),
                    "images": images,
                    "variants": [{
                        "price": str(content.price),
                        "inventory_quantity": content.platform_specific.get("quantity", 999),
                    }],
                }
            }

            status, body = await self._safe_request(
                "POST",
                f"{self.store_url}/admin/api/2024-01/products.json",
                headers={
                    "X-Shopify-Access-Token": self.access_token,
                    "Content-Type": "application/json",
                },
                json_data=product_data,
            )

            product = body.get("product", {})
            if product.get("id"):
                pid = product["id"]
                handle = product.get("handle", "")
                return PublishResult(
                    platform=self.platform, success=True,
                    post_id=str(pid),
                    post_url=f"{self.store_url}/products/{handle}",
                    latency_ms=(time.monotonic() - t0) * 1000,
                )
            else:
                return PublishResult(
                    platform=self.platform, success=False,
                    error=str(body.get("errors", "Failed")),
                )

        except PlatformError as exc:
            return PublishResult(
                platform=self.platform, success=False,
                error=str(exc),
            )


# ═══════════════════════════════════════════════════
# WooCommerce REST API Publisher
# ═══════════════════════════════════════════════════

class WooCommercePublisher(BasePublisher):
    """Create products on WooCommerce via REST API."""
    platform = PlatformType.WOOCOMMERCE

    def __init__(self) -> None:
        super().__init__()
        self.store_url = os.getenv("WOOCOMMERCE_URL", "").rstrip("/")
        self.key = os.getenv("WOOCOMMERCE_API_KEY", "")
        self.secret = os.getenv("WOOCOMMERCE_API_SECRET", "")

    def is_configured(self) -> bool:
        return bool(self.store_url and self.key and self.secret)

    async def publish(self, content: ContentPayload) -> PublishResult:
        if not self.is_configured():
            return PublishResult(
                platform=self.platform, success=False,
                error="WOOCOMMERCE_URL, API_KEY, or API_SECRET not set"
            )

        t0 = time.monotonic()

        try:
            images = [{"src": u} for u in content.image_urls[:10]]
            product_data = {
                "name": content.title,
                "type": "simple",
                "regular_price": str(content.price),
                "description": content.body or content.caption,
                "short_description": content.caption[:200] if content.caption else "",
                "categories": [{"name": content.category}] if content.category else [],
                "tags": [{"name": t} for t in (content.tags or content.hashtags)],
                "images": images,
                "manage_stock": True,
                "stock_quantity": content.platform_specific.get("quantity", 999),
            }

            status, body = await self._safe_request(
                "POST",
                f"{self.store_url}/wp-json/wc/v3/products",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {self._basic_auth()}",
                },
                json_data=product_data,
            )

            if body.get("id"):
                pid = body["id"]
                return PublishResult(
                    platform=self.platform, success=True,
                    post_id=str(pid),
                    post_url=body.get("permalink", ""),
                    latency_ms=(time.monotonic() - t0) * 1000,
                )
            else:
                return PublishResult(
                    platform=self.platform, success=False,
                    error=str(body.get("message", "Failed")),
                )

        except PlatformError as exc:
            return PublishResult(
                platform=self.platform, success=False,
                error=str(exc),
            )

    def _basic_auth(self) -> str:
        import base64
        return base64.b64encode(f"{self.key}:{self.secret}".encode()).decode()


# ═══════════════════════════════════════════════════
# Unified Publisher Manager
# ═══════════════════════════════════════════════════

class PublisherManager:
    """
    Central manager for all platform publishers.
    
    Usage:
        pm = PublisherManager()
        results = await pm.publish_all(content)
        # or
        result = await pm.publish_to(PlatformType.INSTAGRAM, content)
    """

    def __init__(self) -> None:
        self._publishers: Dict[PlatformType, BasePublisher] = {
            PlatformType.TELEGRAM: TelegramPublisher(),
            PlatformType.INSTAGRAM: InstagramPublisher(),
            PlatformType.ETSY: EtsyPublisher(),
            PlatformType.SHOPIFY: ShopifyPublisher(),
            PlatformType.WOOCOMMERCE: WooCommercePublisher(),
        }

    def get_configured_platforms(self) -> List[PlatformType]:
        """Return list of platforms that have API keys set."""
        return [p for p, pub in self._publishers.items() if pub.is_configured()]

    def get_status(self) -> Dict[str, bool]:
        """Return {platform_name: is_configured} for all platforms."""
        return {p.value: pub.is_configured() for p, pub in self._publishers.items()}

    async def publish_to(
        self, platform: PlatformType, content: ContentPayload
    ) -> PublishResult:
        """Publish to a specific platform."""
        pub = self._publishers.get(platform)
        if not pub:
            return PublishResult(
                platform=platform, success=False,
                error=f"Unknown platform: {platform.value}",
            )
        if not pub.is_configured():
            return PublishResult(
                platform=platform, success=False,
                error=f"{platform.value} not configured (missing API keys)",
            )
        return await pub.publish(content)

    async def publish_all(
        self, content: ContentPayload,
        platforms: Optional[List[PlatformType]] = None,
    ) -> List[PublishResult]:
        """
        Publish to all configured platforms (or specified list) in parallel.
        Returns list of results.
        """
        targets = platforms or self.get_configured_platforms()
        if not targets:
            return [PublishResult(
                platform=PlatformType.TELEGRAM, success=False,
                error="No platforms configured. Set API keys in .env",
            )]

        tasks = [self.publish_to(p, content) for p in targets]
        return await asyncio.gather(*tasks)

    async def close(self) -> Any:
        for pub in self._publishers.values():
            await pub.close()


# ═══════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════

_manager: Optional[PublisherManager] = None


def get_publisher_manager() -> PublisherManager:
    global _manager
    if _manager is None:
        _manager = PublisherManager()
    return _manager


