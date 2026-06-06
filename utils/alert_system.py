
"""
Alert System v9.1
Sends alerts to admin via Telegram when critical events occur.
"""
import logging
import time
from typing import Optional, List, Dict, Any
from enum import Enum
from arki_project.exceptions import ArkiBaseError

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    INFO = "ℹ️"
    WARNING = "⚠️"
    ERROR = "❌"
    CRITICAL = "🚨"


class Alert:
    def __init__(self, level: AlertLevel, title: str, message: str) -> None:
        self.level = level
        self.title = title
        self.message = message
        self.timestamp = time.time()

    def format(self) -> str:
        return (
            f"{self.level.value} *{self.title}*\n"
            f"{self.message}\n"
            f"_Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.timestamp))}_"
        )


class AlertSystem:
    """
    Sends alerts to admin Telegram accounts.
    Features:
    - Deduplication (same alert won't repeat within cooldown)
    - Rate limiting (max alerts per hour)
    - Alert history
    """

    def __init__(self, admin_ids: Optional[List[int]] = None, bot: Optional[Any]=None) -> None:
        self.admin_ids = admin_ids or []
        self.bot = bot
        self._history: List[Alert] = []
        self._cooldowns: Dict[str, float] = {}
        self._cooldown_seconds = 300  # 5 min between same alerts
        self._max_per_hour = 30
        self._hourly_count = 0
        self._hour_start = time.time()

    def set_bot(self, bot: Any) -> None:
        """Set the Telegram bot instance for sending."""
        self.bot = bot

    def add_admin(self, user_id: int) -> None:
        if user_id not in self.admin_ids:
            self.admin_ids.append(user_id)

    async def send(self, level: AlertLevel, title: str, message: str) -> Any:
        """Send an alert to all admins."""
        alert = Alert(level, title, message)

        # Dedup check
        alert_key = f"{title}:{message}"
        now = time.time()
        if alert_key in self._cooldowns:
            if now - self._cooldowns[alert_key] < self._cooldown_seconds:
                return  # Skip duplicate

        # Rate limit check
        if now - self._hour_start > 3600:
            self._hourly_count = 0
            self._hour_start = now

        if self._hourly_count >= self._max_per_hour:
            return  # Too many alerts

        # Record
        self._cooldowns[alert_key] = now
        self._hourly_count += 1
        self._history.append(alert)
        if len(self._history) > 1000:
            self._history = self._history[-500:]

        # Send
        formatted = alert.format()
        logger.log(
            logging.CRITICAL if level == AlertLevel.CRITICAL else logging.WARNING,
            "Alert [%s]: %s — %s", level.name, title, message,
        )

        if self.bot and self.admin_ids:
            for admin_id in self.admin_ids:
                try:
                    await self.bot.send_message(
                        admin_id, formatted, parse_mode="Markdown"
                    )
                except ArkiBaseError as e:
                    logger.error("Failed to send alert to %s: %s", admin_id, e)

    async def info(self, title: str, message: str) -> Any:
        await self.send(AlertLevel.INFO, title, message)

    async def warning(self, title: str, message: str) -> Any:
        await self.send(AlertLevel.WARNING, title, message)

    async def error(self, title: str, message: str) -> Any:
        await self.send(AlertLevel.ERROR, title, message)

    async def critical(self, title: str, message: str) -> Any:
        await self.send(AlertLevel.CRITICAL, title, message)

    @property
    def stats(self) -> dict:
        return {
            "total_alerts": len(self._history),
            "hourly_count": self._hourly_count,
            "admin_count": len(self.admin_ids),
        }


# Singleton
_alerts: Optional[AlertSystem] = None

def get_alert_system() -> AlertSystem:
    global _alerts
    if _alerts is None:
        _alerts = AlertSystem()
    return _alerts


