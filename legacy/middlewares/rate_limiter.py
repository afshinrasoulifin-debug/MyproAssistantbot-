
from __future__ import annotations
"""
tg_bot/middlewares/rate_limiter.py
──────────────────────────────────
Sliding-window rate limiter middleware v2.0.

v29.0 TITANIUM:
  • Redis-backed (persistent across restarts) when REDIS_URL is set
  • Falls back to in-memory if Redis is unavailable
  • Persian warning message
  • Progressive warnings (soft limit → hard limit)
  • ✅ Tier-aware enforcement (FREE/PRO/ENTERPRISE/UNLIMITED)
  • ✅ Per-endpoint rate limits (separate limits for /api, /generate, etc.)
  • ✅ Daily limits with midnight reset
  • ✅ Tier loaded from DB on first request, cached
"""


import logging
import os
import time
from collections import defaultdict
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)

# ── Worker ID for distributed coordination ──────────
import uuid as _uuid
_WORKER_ID = _uuid.uuid4().hex[:8]  # Unique per-process

# ── Redis client (optional) ──────────────────────────
_redis_client = None
_redis_available = None  # None=untested, True/False=tested


async def _get_redis():
    """Lazy-init Redis client from REDIS_URL env var.

    Returns None if Redis is unavailable (graceful fallback to memory).
    """
    global _redis_client, _redis_available

    if _redis_available is False:
        return None

    if _redis_client is not None:
        return _redis_client

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        _redis_available = False
        return None

    try:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=3,
            socket_connect_timeout=3,
            retry_on_timeout=True,
        )
        await _redis_client.ping()
        _redis_available = True
        logger.info("Rate limiter: Redis connected (worker=%s)", _WORKER_ID)
        return _redis_client
    except Exception as e:
        logger.warning("Rate limiter: Redis unavailable (%s), using memory", e)
        _redis_available = False
        _redis_client = None
        return None


# ── Tier system ──────────────────────────────────────

class UserTier(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"


# Per-minute and daily limits per tier
TIER_LIMITS: Dict[UserTier, Dict[str, int]] = {
    UserTier.FREE:       {"requests_per_min": 20,     "daily_limit": 500},
    UserTier.PRO:        {"requests_per_min": 60,     "daily_limit": 5000},
    UserTier.ENTERPRISE: {"requests_per_min": 120,    "daily_limit": 50000},
    UserTier.UNLIMITED:  {"requests_per_min": 999999, "daily_limit": 9999999},
}

# Per-endpoint extra limits (commands that are expensive get lower limits)
ENDPOINT_LIMITS: Dict[str, Dict[UserTier, int]] = {
    # endpoint_name: {tier: max_per_minute}
    "generate":  {UserTier.FREE: 5,  UserTier.PRO: 20, UserTier.ENTERPRISE: 60,  UserTier.UNLIMITED: 999999},
    "api_call":  {UserTier.FREE: 3,  UserTier.PRO: 15, UserTier.ENTERPRISE: 50,  UserTier.UNLIMITED: 999999},
    "image":     {UserTier.FREE: 2,  UserTier.PRO: 10, UserTier.ENTERPRISE: 30,  UserTier.UNLIMITED: 999999},
    "search":    {UserTier.FREE: 5,  UserTier.PRO: 20, UserTier.ENTERPRISE: 60,  UserTier.UNLIMITED: 999999},
    "pipeline":  {UserTier.FREE: 2,  UserTier.PRO: 10, UserTier.ENTERPRISE: 40,  UserTier.UNLIMITED: 999999},
}

# In-memory tier cache (loaded from DB on demand)
_user_tiers: Dict[int, UserTier] = {}
_tier_cache_ttl: Dict[int, float] = {}  # user_id → last_loaded_timestamp
_TIER_CACHE_TTL = 300  # Reload tier from DB every 5 min


async def _load_tier_from_db(user_id: int) -> UserTier:
    """Load user tier from database. Falls back to FREE if not found."""
    try:
        from database.connection import get_session
        from sqlalchemy import text
        async with get_session() as session:
            result = await session.execute(
                text("SELECT tier FROM users WHERE telegram_id = :uid"),
                {"uid": user_id},
            )
            row = result.fetchone()
            if row and row[0]:
                try:
                    return UserTier(row[0])
                except ValueError:
                    pass
    except Exception as e:
        logger.debug("Tier DB lookup failed for user %d: %s", user_id, e)
    return UserTier.FREE


async def get_user_tier(user_id: int) -> UserTier:
    """Get user tier (cached, DB-backed)."""
    now = time.time()

    # Check cache
    if user_id in _user_tiers:
        if now - _tier_cache_ttl.get(user_id, 0) < _TIER_CACHE_TTL:
            return _user_tiers[user_id]

    # Load from DB
    tier = await _load_tier_from_db(user_id)
    _user_tiers[user_id] = tier
    _tier_cache_ttl[user_id] = now
    return tier


def set_user_tier(user_id: int, tier: UserTier):
    """Set user tier (in-memory cache — DB update is caller's responsibility)."""
    _user_tiers[user_id] = tier
    _tier_cache_ttl[user_id] = time.time()


def get_user_limits(user_id: int) -> dict:
    """Get rate limits for a user based on cached tier."""
    tier = _user_tiers.get(user_id, UserTier.FREE)
    return TIER_LIMITS[tier]


# ── Daily limit tracking ─────────────────────────────

def _daily_key(user_id: int) -> str:
    """Redis key for daily limit tracking."""
    import datetime
    today = datetime.date.today().isoformat()
    return f"ratelimit:daily:{user_id}:{today}"


class RateLimiterMiddleware(BaseMiddleware):
    """
    Sliding-window rate limiter with Redis persistence.

    v29.0: Tier-aware, per-endpoint, daily limits.

    Parameters
    ----------
    max_messages : int
        Default maximum messages per window (overridden by tier).
    window_seconds : int
        Size of the sliding window in seconds.
    admin_ids : list[int]
        Telegram user IDs exempt from rate limiting.
    """

    def __init__(
        self,
        max_messages: int = 50,
        window_seconds: int = 60,
        admin_ids: list[int] | None = None,
    ) -> None:
        self._default_max = max_messages
        self._window = window_seconds
        self._admin_ids = set(admin_ids or [])
        # In-memory fallback
        self._user_hits: Dict[int, List[float]] = defaultdict(list)
        self._daily_counts: Dict[str, int] = defaultdict(int)
        self._last_warned: Dict[int, float] = {}

    async def _check_redis(self, user_id: int, now: float, key_suffix: str = "") -> Optional[int]:
        """Check rate limit via Redis using atomic pipeline.

        v29.0: Worker-ID tagged entries for distributed coordination.
        Returns hit count or None if Redis unavailable.
        """
        r = await _get_redis()
        if not r:
            return None

        try:
            key = f"ratelimit:{user_id}{key_suffix}"
            member = f"{_WORKER_ID}:{now}"

            pipe = r.pipeline(transaction=True)
            pipe.zremrangebyscore(key, 0, now - self._window)
            pipe.zadd(key, {member: now})
            pipe.zcard(key)
            pipe.expire(key, int(self._window) + 10)
            results = await pipe.execute()
            return results[2]
        except Exception as e:
            logger.debug("Redis rate limit error (worker=%s): %s", _WORKER_ID, e)
            return None

    async def _check_daily_redis(self, user_id: int) -> Optional[int]:
        """Check daily limit via Redis."""
        r = await _get_redis()
        if not r:
            return None

        try:
            key = _daily_key(user_id)
            pipe = r.pipeline(transaction=True)
            pipe.incr(key)
            pipe.expire(key, 86400)  # 24h TTL
            results = await pipe.execute()
            return results[0]  # Current count after increment
        except Exception:
            return None

    def _check_memory(self, user_id: int, now: float) -> int:
        """In-memory fallback rate check.

        WARNING: In multi-worker deployments, in-memory fallback only tracks
        this worker's requests. Use Redis for production.
        """
        hits = self._user_hits[user_id]
        cutoff = now - self._window
        self._user_hits[user_id] = hits = [t for t in hits if t > cutoff]
        hits.append(now)
        return len(hits)

    def _check_daily_memory(self, user_id: int) -> int:
        """In-memory daily counter."""
        key = _daily_key(user_id)
        self._daily_counts[key] += 1
        return self._daily_counts[key]

    def _detect_endpoint(self, event: TelegramObject) -> str:
        """Detect which endpoint/command is being called."""
        try:
            msg = getattr(event, "message", event)
            text = getattr(msg, "text", "") or ""
            if text.startswith("/"):
                cmd = text.split()[0].split("@")[0].lstrip("/").lower()
                # Map commands to endpoint categories
                if cmd in ("generate", "gen", "create"):
                    return "generate"
                elif cmd in ("api", "apicall", "call"):
                    return "api_call"
                elif cmd in ("image", "img", "photo"):
                    return "image"
                elif cmd in ("search", "find", "query"):
                    return "search"
                elif cmd in ("pipeline", "pipe", "flow"):
                    return "pipeline"
        except Exception:
            pass
        return "general"

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        user_id: int = tg_user.id

        # Admins bypass rate limiting
        if user_id in self._admin_ids:
            return await handler(event, data)

        now = time.time()

        # v29: Load user tier
        tier = await get_user_tier(user_id)
        tier_limits = TIER_LIMITS[tier]
        max_per_min = tier_limits["requests_per_min"]
        daily_limit = tier_limits["daily_limit"]

        # ── 1. Check per-minute rate limit ──
        count = await self._check_redis(user_id, now)
        if count is None:
            count = self._check_memory(user_id, now)

        if count >= max_per_min:
            logger.info(
                "Rate limit hit: user %d (tier=%s, %d msgs in %ds)",
                user_id, tier.value, count, self._window,
            )
            try:
                msg = getattr(event, "message", event)
                if hasattr(msg, "answer"):
                    await msg.answer(
                        f"⚠️ محدودیت ارسال پیام\n"
                        f"سطح شما: {tier.value.upper()}\n"
                        f"حداکثر {max_per_min} پیام در دقیقه\n"
                        f"لطفاً چند لحظه صبر کنید."
                    )
            except Exception as _exc:
                logger.debug("Rate limit reply failed: %s", _exc)
            return  # Block

        # ── 2. Check daily limit ──
        daily_count = await self._check_daily_redis(user_id)
        if daily_count is None:
            daily_count = self._check_daily_memory(user_id)

        if daily_count >= daily_limit:
            logger.info(
                "Daily limit hit: user %d (tier=%s, %d/%d)",
                user_id, tier.value, daily_count, daily_limit,
            )
            try:
                msg = getattr(event, "message", event)
                if hasattr(msg, "answer"):
                    remaining_hours = 24 - (time.localtime().tm_hour)
                    await msg.answer(
                        f"⚠️ محدودیت روزانه\n"
                        f"سطح شما: {tier.value.upper()} — {daily_limit} پیام در روز\n"
                        f"تقریباً {remaining_hours} ساعت تا بازنشانی."
                    )
            except Exception:
                pass
            return  # Block

        # ── 3. Check per-endpoint limit ──
        endpoint = self._detect_endpoint(event)
        if endpoint in ENDPOINT_LIMITS:
            ep_max = ENDPOINT_LIMITS[endpoint].get(tier, max_per_min)
            ep_count = await self._check_redis(user_id, now, key_suffix=f":ep:{endpoint}")
            if ep_count is None:
                # For memory fallback, use same mechanism with prefixed key
                ep_key = f"{user_id}:ep:{endpoint}"
                ep_hits = self._user_hits[ep_key]
                cutoff = now - self._window
                self._user_hits[ep_key] = ep_hits = [t for t in ep_hits if t > cutoff]
                ep_hits.append(now)
                ep_count = len(ep_hits)

            if ep_count >= ep_max:
                logger.info(
                    "Endpoint limit hit: user %d, endpoint=%s (%d/%d)",
                    user_id, endpoint, ep_count, ep_max,
                )
                try:
                    msg = getattr(event, "message", event)
                    if hasattr(msg, "answer"):
                        await msg.answer(
                            f"⚠️ محدودیت دستور /{endpoint}\n"
                            f"حداکثر {ep_max} بار در دقیقه (سطح {tier.value.upper()})"
                        )
                except Exception:
                    pass
                return  # Block

        # ── 4. Soft warning at 80% ──
        soft_limit = int(max_per_min * 0.8)
        if count >= soft_limit:
            last_warn = self._last_warned.get(user_id, 0)
            if now - last_warn > 30:
                self._last_warned[user_id] = now
                remaining = max_per_min - count
                try:
                    msg = getattr(event, "message", event)
                    if hasattr(msg, "answer"):
                        await msg.answer(
                            f"⚠️ {remaining} پیام باقی‌مانده در این بازه "
                            f"({tier.value.upper()})"
                        )
                except Exception:
                    pass

        # ── 5. Periodic cleanup ──
        if len(self._user_hits) > 500:
            cutoff = now - self._window
            self._user_hits = {
                uid: ts_list
                for uid, ts_list in self._user_hits.items()
                if ts_list and ts_list[-1] > cutoff
            }
            self._last_warned = {
                uid: ts for uid, ts in self._last_warned.items()
                if ts > cutoff
            }

        # Clean stale daily counts (keys from previous days)
        if len(self._daily_counts) > 1000:
            import datetime
            today = datetime.date.today().isoformat()
            self._daily_counts = {
                k: v for k, v in self._daily_counts.items()
                if today in k
            }

        return await handler(event, data)


