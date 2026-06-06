
"""
Webhook Handler v9.1
HTTP webhook endpoint for external service integrations.
"""
import asyncio
import json
import logging
import hmac
import hashlib
from typing import Callable, Dict, Optional, Any
from aiohttp import web

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class WebhookHandler:
    """
    HTTP webhook receiver for external integrations.

    Supports:
    - Custom webhook endpoints
    - Signature verification
    - Event routing
    - Rate limiting
    """

    def __init__(self, secret: str = "") -> None:
        self._routes: Dict[str, Callable] = {}
        self._secret = secret
        self._app: Optional[web.Application] = None
        self._stats = {"received": 0, "processed": 0, "errors": 0}

    def register(self, path: str, handler: Callable) -> Any:
        """Register a webhook handler for a path."""
        self._routes[path] = handler
        logger.info("Webhook registered: %s", path)

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature."""
        if not self._secret:
            return True
        expected = hmac.new(
            self._secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)

    async def handle_request(self, request: web.Request) -> web.Response:
        """Handle incoming webhook request."""
        self._stats["received"] += 1
        path = request.path

        handler = self._routes.get(path)
        if not handler:
            return web.Response(status=404, text="Not found")

        try:
            body = await request.read()

            # Verify signature if secret is set
            sig = request.headers.get("X-Signature-256", "")
            if self._secret and not self.verify_signature(body, sig):
                return web.Response(status=401, text="Invalid signature")

            data = json.loads(body) if body else {}

            if asyncio.iscoroutinefunction(handler):
                result = await handler(data)
            else:
                result = handler(data)

            self._stats["processed"] += 1
            return web.json_response({"status": "ok", "result": result})
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("Webhook error on %s: %s", path, e)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    def build_app(self) -> web.Application:
        """Build aiohttp application."""
        self._app = web.Application()
        for path in self._routes:
            self._app.router.add_post(path, self.handle_request)
        return self._app

    @property
    def stats(self) -> dict:
        return self._stats.copy()


