
from __future__ import annotations
"""Victor v7.0 TITAN — Security (InputGuard) & Backup"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .files import FileProcessor

# ═══════════════════════════════════════════════════════════════════
# INPUT GUARD — v7 TITAN Security & Protection Layer
# ═══════════════════════════════════════════════════════════════════

class InputGuard:
    """
    Real protection layer for Victor:
    - Rate limiting per user
    - Input sanitization (injection prevention)
    - Size limits
    - Flood detection
    - Content validation
    - Suspicious pattern detection
    - Auto-backup trigger
    """

    # Limits
    MAX_MESSAGE_LENGTH = 4000
    MAX_MESSAGES_PER_MINUTE = 15
    MAX_MESSAGES_PER_HOUR = 200
    MAX_TEACH_PER_HOUR = 50
    MAX_FILE_SIZE_MB = 20

    # Dangerous patterns
    INJECTION_PATTERNS = [
        r'(?:DROP|DELETE|UPDATE|INSERT|ALTER)\s+(?:TABLE|DATABASE|FROM)',
        r'<\s*script\b',
        r'javascript\s*:',
        r'on(?:error|load|click|mouseover)\s*=',
        r'\{\{.*\}\}',          # Template injection
        r'\$\{.*\}',            # Variable injection
        r'__(?:import|class|subclasses)__',  # Python injection
        r'(?:eval|exec|compile)\s*\(',
        r'os\.(?:system|popen|exec)',
        r'subprocess\.',
        r'\\x[0-9a-fA-F]{2}',  # Hex escape sequences
    ]

    # Compiled patterns for speed
    _compiled_patterns = None

    def __init__(self) -> None:
        self._rate_limits: Dict[int, List[float]] = {}  # user_id → timestamps
        self._teach_limits: Dict[int, List[float]] = {}
        self._blocked_users: Dict[int, float] = {}  # user_id → blocked_until
        self._violation_counts: Dict[int, int] = {}  # user_id → count
        self._flood_tracker: Dict[int, List[str]] = {}  # user_id → recent messages
        if InputGuard._compiled_patterns is None:
            InputGuard._compiled_patterns = [
                re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS
            ]

    def check(self, text: str, user_id: int = 0,
              action: str = "message") -> Tuple[bool, str]:
        """
        Main protection check. Returns (is_safe, reason).
        is_safe=True means the message can proceed.
        """
        now = time.time()

        # 1. Check if user is blocked
        if user_id in self._blocked_users:
            if now < self._blocked_users[user_id]:
                remaining = int(self._blocked_users[user_id] - now)
                return False, f"⛔ دسترسی شما موقتاً محدود شده. {remaining} ثانیه صبر کنید."
            else:
                del self._blocked_users[user_id]

        # 2. Size check
        if len(text) > self.MAX_MESSAGE_LENGTH:
            return False, f"⚠️ پیام خیلی بلنده (حداکثر {self.MAX_MESSAGE_LENGTH} کاراکتر). لطفاً کوتاه‌تر بنویسید."

        # 3. Empty / whitespace
        if not text.strip():
            return False, ""

        # 4. Rate limiting
        rate_ok, rate_msg = self._check_rate_limit(user_id, action, now)
        if not rate_ok:
            return False, rate_msg

        # 5. Flood detection (same message repeated)
        if user_id:
            flood_ok, flood_msg = self._check_flood(user_id, text, now)
            if not flood_ok:
                return False, flood_msg

        # 6. Injection detection
        injection_ok, injection_msg = self._check_injection(text)
        if not injection_ok:
            self._record_violation(user_id)
            return False, injection_msg

        # 7. Content validation
        valid_ok, valid_msg = self._validate_content(text, action)
        if not valid_ok:
            return False, valid_msg

        return True, ""

    def _check_rate_limit(self, user_id: int, action: str,
                          now: float) -> Tuple[bool, str]:
        """Per-user rate limiting."""
        if not user_id:
            return True, ""

        # Clean old timestamps
        if user_id not in self._rate_limits:
            self._rate_limits[user_id] = []

        self._rate_limits[user_id] = [
            ts for ts in self._rate_limits[user_id]
            if now - ts < 3600
        ]

        timestamps = self._rate_limits[user_id]

        # Per-minute check
        recent_minute = sum(1 for ts in timestamps if now - ts < 60)
        if recent_minute >= self.MAX_MESSAGES_PER_MINUTE:
            return False, "⚠️ لطفاً یکم آرام‌تر! حداکثر 15 پیام در دقیقه."

        # Per-hour check
        if len(timestamps) >= self.MAX_MESSAGES_PER_HOUR:
            return False, "⚠️ محدودیت ساعتی. لطفاً بعداً دوباره امتحان کنید."

        # Teach-specific limit
        if action == "teach":
            if user_id not in self._teach_limits:
                self._teach_limits[user_id] = []
            self._teach_limits[user_id] = [
                ts for ts in self._teach_limits[user_id]
                if now - ts < 3600
            ]
            if len(self._teach_limits[user_id]) >= self.MAX_TEACH_PER_HOUR:
                return False, "⚠️ محدودیت آموزش (50 در ساعت). بعداً ادامه بده."
            self._teach_limits[user_id].append(now)

        timestamps.append(now)
        return True, ""

    def _check_flood(self, user_id: int, text: str,
                     now: float) -> Tuple[bool, str]:
        """Detect repeated identical messages (flood)."""
        if user_id not in self._flood_tracker:
            self._flood_tracker[user_id] = []

        recent = self._flood_tracker[user_id]
        text_norm = text.strip().lower()[:100]

        # Count recent duplicates
        duplicate_count = sum(1 for msg in recent[-10:] if msg == text_norm)

        if duplicate_count >= 3:
            self._record_violation(user_id)
            return False, "⚠️ پیام تکراری. لطفاً پیام متفاوتی بنویسید."

        recent.append(text_norm)
        # Keep last 20
        self._flood_tracker[user_id] = recent[-20:]
        return True, ""

    def _check_injection(self, text: str) -> Tuple[bool, str]:
        """Detect potential injection attacks."""
        for pattern in self._compiled_patterns:
            if pattern.search(text):
                return False, "⚠️ محتوای مشکوک شناسایی شد. لطفاً از کاراکترهای ساده استفاده کنید."

        # Check for excessive special characters
        special_ratio = sum(1 for c in text if c in '{}[]<>|\\`$') / max(1, len(text))
        if special_ratio > 0.3:
            return False, "⚠️ تعداد کاراکترهای خاص زیاده."

        return True, ""

    def _validate_content(self, text: str, action: str) -> Tuple[bool, str]:
        """Validate content based on action type."""
        if action == "teach":
            # Teaching content should have at least some substance
            if len(text.split()) < 3:
                return False, "⚠️ محتوای آموزشی باید حداقل ۳ کلمه باشد."

            # Check for gibberish (too many consonants without vowels in English)
            if re.match(r'^[bcdfghjklmnpqrstvwxyz]{10,}$', text.lower()):
                return False, "⚠️ محتوا معتبر به نظر نمی‌رسه."

        elif action == "file_create":
            # Filename validation
            pass

        return True, ""

    def _record_violation(self, user_id: int) -> Any:
        """Record a security violation. Auto-block on repeated offenses."""
        if not user_id:
            return

        self._violation_counts[user_id] = self._violation_counts.get(user_id, 0) + 1
        count = self._violation_counts[user_id]

        if count >= 10:
            # Block for 1 hour
            self._blocked_users[user_id] = time.time() + 3600
        elif count >= 5:
            # Block for 5 minutes
            self._blocked_users[user_id] = time.time() + 300
        elif count >= 3:
            # Block for 1 minute
            self._blocked_users[user_id] = time.time() + 60

    def check_file_upload(self, file_size: int, file_name: str) -> Tuple[bool, str]:
        """Validate file uploads."""
        max_bytes = self.MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            return False, f"⚠️ فایل بزرگ‌تر از {self.MAX_FILE_SIZE_MB}MB است."

        # Check for dangerous extensions
        dangerous_ext = {'.exe', '.bat', '.cmd', '.scr', '.pif', '.com',
                         '.vbs', '.vbe', '.js', '.jse', '.wsh', '.wsf',
                         '.ps1', '.msi', '.dll', '.sys'}
        ext = Path(file_name).suffix.lower() if file_name else ""
        if ext in dangerous_ext:
            return False, f"⚠️ فایل‌های {ext} پشتیبانی نمی‌شوند (امنیتی)."

        return True, ""

    def get_user_status(self, user_id: int) -> Dict[str, Any]:
        """Get security status for a user."""
        now = time.time()
        timestamps = self._rate_limits.get(user_id, [])
        recent = sum(1 for ts in timestamps if now - ts < 60)
        hourly = sum(1 for ts in timestamps if now - ts < 3600)

        return {
            "messages_this_minute": recent,
            "messages_this_hour": hourly,
            "violations": self._violation_counts.get(user_id, 0),
            "is_blocked": user_id in self._blocked_users and now < self._blocked_users.get(user_id, 0),
            "blocked_until": self._blocked_users.get(user_id, 0) if user_id in self._blocked_users else None,
        }

    def format_status(self, user_id: int) -> str:
        """Format protection status for display."""
        status = self.get_user_status(user_id)
        return (
            f"🛡️ *وضعیت امنیتی:*\n\n"
            f"  📊 پیام این دقیقه: {status['messages_this_minute']}/{self.MAX_MESSAGES_PER_MINUTE}\n"
            f"  📊 پیام این ساعت: {status['messages_this_hour']}/{self.MAX_MESSAGES_PER_HOUR}\n"
            f"  ⚠️ تخلفات: {status['violations']}\n"
            f"  {'⛔ مسدود' if status['is_blocked'] else '✅ فعال'}"
        )

# ═══════════════════════════════════════════════════════════════════
# MEMORY BACKUP — v7 TITAN Data Protection
# ═══════════════════════════════════════════════════════════════════

class MemoryBackup:
    """
    Automatic backup system for Victor's brain data.
    - Periodic auto-backup
    - Before dangerous operations
    - Restore capability
    - Backup rotation (keep last N)
    """

    MAX_BACKUPS = 10

    def __init__(self, brain_dir: Path) -> None:
        self.brain_dir = brain_dir
        self.backup_dir = brain_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._last_backup: float = 0.0

    def create_backup(self, reason: str = "auto") -> str:
        """Create a backup of all brain data."""
        import zipfile
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"brain_backup_{ts}_{reason}.zip"
        backup_path = self.backup_dir / backup_name

        try:
            files_to_backup = [
                "memories.json",
                "graph.json",
                "rules.json",
                "patterns.json",
                "interactions.json",
                "semantic_index.json",
                "personality.json",
            ]

            with zipfile.ZipFile(str(backup_path), "w", zipfile.ZIP_DEFLATED) as zf:
                for fname in files_to_backup:
                    fpath = self.brain_dir / fname
                    if fpath.exists():
                        zf.write(str(fpath), fname)

            # Rotate old backups
            self._rotate_backups()

            size = backup_path.stat().st_size
            self._last_backup = time.time()

            return (
                f"✅ بک‌آپ ایجاد شد!\n"
                f"📂 `{backup_name}`\n"
                f"📏 حجم: {FileProcessor._format_size(size)}\n"
                f"📋 دلیل: {reason}"
            )
        except Exception as e:
            return f"❌ خطا در بک‌آپ: {e}"

    def restore_backup(self, backup_name: str = "") -> str:
        """Restore from a backup."""
        import zipfile

        if not backup_name:
            # Use latest backup
            backups = self.list_backups()
            if not backups:
                return "❌ بک‌آپی وجود نداره."
            backup_name = backups[0]["name"]

        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            return f"❌ بک‌آپ `{backup_name}` پیدا نشد."

        try:
            # Create a safety backup before restore
            self.create_backup(reason="pre_restore")

            with zipfile.ZipFile(str(backup_path), "r") as zf:
                zf.extractall(str(self.brain_dir))

            return f"✅ بازیابی از `{backup_name}` انجام شد! ریستارت لازمه."
        except Exception as e:
            return f"❌ خطا در بازیابی: {e}"

    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups."""
        backups = []
        for f in sorted(self.backup_dir.iterdir(), reverse=True):
            if f.suffix == ".zip" and f.name.startswith("brain_backup_"):
                backups.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "created": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                })
        return backups

    def _rotate_backups(self) -> Any:
        """Keep only the last MAX_BACKUPS backups."""
        backups = sorted(
            [f for f in self.backup_dir.iterdir() if f.suffix == ".zip"],
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        for old_backup in backups[self.MAX_BACKUPS:]:
            old_backup.unlink()

    def should_auto_backup(self) -> bool:
        """Check if it's time for auto-backup (every 6 hours)."""
        return time.time() - self._last_backup > 6 * 3600

    def format_list(self) -> str:
        """Format backup list for display."""
        backups = self.list_backups()
        if not backups:
            return "📦 هیچ بک‌آپی وجود نداره."

        lines = [f"📦 *بک‌آپ‌ها ({len(backups)}):*\n"]
        for b in backups:
            size = FileProcessor._format_size(b["size"])
            lines.append(f"  • `{b['name']}` ({size}) — {b['created']}")
        return "\n".join(lines)


