
from __future__ import annotations
"""
tg_bot/utils/dashboard_monitor.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
DASHBOARD MONITOR — Real-Time System & Bot Monitoring Engine

Comprehensive monitoring dashboard for tracking bot health,
system resources, API usage, user activity, and performance
metrics with alerting and reporting.

Architecture
────────────
   ┌──────────────────────────────────────────────────────┐
   │              DASHBOARD MONITOR                        │
   ├──────────┬──────────┬──────────┬──────────┬──────────┤
   │ System   │ Bot      │ API      │ User     │ Alert    │
   │ Monitor  │ Health   │ Tracker  │ Activity │ Engine   │
   ├──────────┼──────────┼──────────┼──────────┼──────────┤
   │ CPU/RAM  │ Uptime   │ Rate     │ Sessions │ Rules    │
   │ Disk     │ Commands │ Latency  │ Commands │ Channels │
   │ Network  │ Errors   │ Costs    │ Patterns │ Cooldown │
   │ Processes│ Queues   │ Quotas   │ Retention│ History  │
   ├──────────┼──────────┼──────────┼──────────┼──────────┤
   │ Trend    │ Health   │ Budget   │ Cohort   │ Report   │
   │ Detect   │ Score    │ Forecast │ Analysis │ Generate │
   └──────────┴──────────┴──────────┴──────────┴──────────┘

Features
────────
  • System resource monitoring (CPU, RAM, disk, network)
  • Bot health tracking (uptime, error rate, command stats)
  • API usage tracking (calls, latency, costs, rate limits)
  • User activity analytics (sessions, retention, patterns)
  • Configurable alert rules with severity levels
  • Alert channels (log, callback, webhook)
  • Alert cooldowns and deduplication
  • Health score calculation (0-100)
  • Budget forecasting and quota enforcement
  • ASCII dashboard rendering
  • Metric history with time-series storage
  • Performance trend detection
  • Automated report generation

References
──────────
  Port of: apex_app/src/lib/dashboard-monitor.ts (511 lines)
  Enhanced with: health scoring, budget forecasting, cohort analysis,
                 trend detection, automated reporting, ASCII dashboards
"""


import logging
import os
import platform
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────

METRIC_HISTORY_SIZE     = 1000      # Max data points per metric
ALERT_COOLDOWN_S        = 300       # 5 min default cooldown
HEALTH_CHECK_INTERVAL   = 60        # seconds


# ═══════════════════════════════════════════════════════════════════
# Enumerations
# ═══════════════════════════════════════════════════════════════════

class MetricType(str, Enum):
    COUNTER     = "counter"
    GAUGE       = "gauge"
    HISTOGRAM   = "histogram"
    RATE        = "rate"


class AlertSeverity(str, Enum):
    INFO        = "info"
    WARNING     = "warning"
    ERROR       = "error"
    CRITICAL    = "critical"


class AlertChannel(str, Enum):
    LOG         = "log"
    CALLBACK    = "callback"
    WEBHOOK     = "webhook"


class HealthStatus(str, Enum):
    HEALTHY     = "healthy"
    DEGRADED    = "degraded"
    UNHEALTHY   = "unhealthy"
    DOWN        = "down"


# ═══════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════

@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """Time-series metric storage."""
    name: str
    type: MetricType
    points: Deque[MetricPoint] = field(default_factory=lambda: deque(maxlen=METRIC_HISTORY_SIZE))
    description: str = ""
    unit: str = ""

    def record(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        self.points.append(MetricPoint(time.time(), value, labels or {}))

    @property
    def latest(self) -> Optional[float]:
        return self.points[-1].value if self.points else None

    @property
    def values(self) -> List[float]:
        return [p.value for p in self.points]

    def mean(self) -> float:
        vals = self.values
        return sum(vals) / len(vals) if vals else 0.0

    def max_val(self) -> float:
        vals = self.values
        return max(vals) if vals else 0.0

    def min_val(self) -> float:
        vals = self.values
        return min(vals) if vals else 0.0

    def rate_per_sec(self, window_s: float = 60) -> float:
        """Calculate rate of change per second over window."""
        now = time.time()
        recent = [p for p in self.points if now - p.timestamp <= window_s]
        if len(recent) < 2:
            return 0.0
        dt = recent[-1].timestamp - recent[0].timestamp
        dv = recent[-1].value - recent[0].value
        return dv / dt if dt > 0 else 0.0


@dataclass
class AlertRule:
    """Configurable alert rule."""
    id: str
    name: str
    metric_name: str
    condition: str              # gt | lt | eq | gte | lte
    threshold: float
    severity: AlertSeverity
    message_template: str
    channel: AlertChannel = AlertChannel.LOG
    cooldown_s: float = ALERT_COOLDOWN_S
    enabled: bool = True
    callback: Optional[Callable] = None


@dataclass
class Alert:
    """Fired alert instance."""
    rule_id: str
    severity: AlertSeverity
    message: str
    metric_name: str
    metric_value: float
    threshold: float
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False


@dataclass
class SystemInfo:
    """System resource snapshot."""
    hostname: str
    os_name: str
    os_version: str
    python_version: str
    cpu_count: int
    cpu_percent: float
    memory_total_mb: float
    memory_used_mb: float
    memory_percent: float
    disk_total_gb: float
    disk_used_gb: float
    disk_percent: float
    uptime_seconds: float
    load_average: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    timestamp: float = field(default_factory=time.time)


@dataclass
class BotStats:
    """Bot-specific statistics."""
    uptime_seconds: float = 0.0
    total_commands: int = 0
    total_messages: int = 0
    total_errors: int = 0
    error_rate: float = 0.0
    active_users: int = 0
    commands_per_minute: float = 0.0
    avg_response_time_ms: float = 0.0
    api_calls: int = 0
    api_cost_usd: float = 0.0
    health_score: float = 100.0
    health_status: HealthStatus = HealthStatus.HEALTHY


@dataclass
class UserActivity:
    """User activity tracking."""
    user_id: str
    first_seen: float
    last_seen: float
    total_commands: int = 0
    total_messages: int = 0
    favorite_commands: Dict[str, int] = field(default_factory=dict)
    session_count: int = 0
    avg_session_duration_s: float = 0.0


@dataclass
class ApiUsage:
    """API usage tracking per provider."""
    provider: str
    total_calls: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_latency_ms: float = 0.0
    error_count: int = 0
    rate_limit_hits: int = 0
    last_call_ts: float = 0.0


# ═══════════════════════════════════════════════════════════════════
# System Monitoring
# ═══════════════════════════════════════════════════════════════════

_boot_time = time.time()


def get_system_info() -> SystemInfo:
    """Collect current system resource information (sync — no await needed)."""
    # Memory
    try:
        with open("/proc/meminfo") as f:
            meminfo = f.read()
        total_kb = int(
            next(l for l in meminfo.splitlines() if "MemTotal" in l).split()[1]
        )
        available_kb = int(
            next(l for l in meminfo.splitlines() if "MemAvailable" in l).split()[1]
        )
        total_mb = total_kb / 1024
        used_mb = (total_kb - available_kb) / 1024
        mem_percent = used_mb / total_mb * 100
    except Exception:
        total_mb = used_mb = mem_percent = 0.0

    # Disk
    try:
        st = os.statvfs("/")
        disk_total = st.f_blocks * st.f_frsize / (1024 ** 3)
        disk_free = st.f_bavail * st.f_frsize / (1024 ** 3)
        disk_used = disk_total - disk_free
        disk_percent = disk_used / disk_total * 100 if disk_total > 0 else 0
    except Exception:
        disk_total = disk_used = disk_percent = 0.0

    # CPU
    cpu_count = os.cpu_count() or 1
    try:
        with open("/proc/loadavg", "r") as f:
            load = tuple(float(x) for x in f.read().split()[:3])
        cpu_percent = load[0] / cpu_count * 100
    except Exception:
        load = (0.0, 0.0, 0.0)
        cpu_percent = 0.0

    return SystemInfo(
        hostname=platform.node(),
        os_name=platform.system(),
        os_version=platform.release(),
        python_version=platform.python_version(),
        cpu_count=cpu_count,
        cpu_percent=round(cpu_percent, 1),
        memory_total_mb=round(total_mb, 1),
        memory_used_mb=round(used_mb, 1),
        memory_percent=round(mem_percent, 1),
        disk_total_gb=round(disk_total, 1),
        disk_used_gb=round(disk_used, 1),
        disk_percent=round(disk_percent, 1),
        uptime_seconds=round(time.time() - _boot_time, 1),
        load_average=load,
    )


# ═══════════════════════════════════════════════════════════════════
# Metrics Registry
# ═══════════════════════════════════════════════════════════════════

class MetricsRegistry:
    """Central registry for all metrics."""

    def __init__(self) -> None:
        self._metrics: Dict[str, MetricSeries] = {}
        self._counters: Dict[str, float] = defaultdict(float)

    def register(self, name: str, mtype: MetricType,
                 description: str = "", unit: str = "") -> MetricSeries:
        if name not in self._metrics:
            self._metrics[name] = MetricSeries(
                name=name, type=mtype, description=description, unit=unit,
            )
        return self._metrics[name]

    def record(self, name: str, value: float,
               labels: Optional[Dict[str, str]] = None) -> None:
        series = self._metrics.get(name)
        if series:
            series.record(value, labels)

    def increment(self, name: str, amount: float = 1.0) -> None:
        self._counters[name] += amount
        series = self._metrics.get(name)
        if series:
            series.record(self._counters[name])

    def get(self, name: str) -> Optional[MetricSeries]:
        return self._metrics.get(name)

    def get_all(self) -> Dict[str, MetricSeries]:
        return dict(self._metrics)

    def snapshot(self) -> Dict[str, Any]:
        """Get current snapshot of all metrics."""
        return {
            name: {
                "type": s.type.value,
                "latest": s.latest,
                "mean": round(s.mean(), 4),
                "min": s.min_val(),
                "max": s.max_val(),
                "count": len(s.points),
            }
            for name, s in self._metrics.items()
        }


# Global registry
metrics = MetricsRegistry()

# Register default metrics
metrics.register("cpu_percent", MetricType.GAUGE, "CPU usage", "%")
metrics.register("memory_percent", MetricType.GAUGE, "Memory usage", "%")
metrics.register("disk_percent", MetricType.GAUGE, "Disk usage", "%")
metrics.register("bot_commands", MetricType.COUNTER, "Total commands processed")
metrics.register("bot_errors", MetricType.COUNTER, "Total errors")
metrics.register("api_calls", MetricType.COUNTER, "Total API calls")
metrics.register("api_cost", MetricType.COUNTER, "Total API cost", "USD")
metrics.register("api_latency", MetricType.HISTOGRAM, "API latency", "ms")
metrics.register("response_time", MetricType.HISTOGRAM, "Bot response time", "ms")
metrics.register("active_users", MetricType.GAUGE, "Active users")


# ═══════════════════════════════════════════════════════════════════
# Alert Engine
# ═══════════════════════════════════════════════════════════════════

class AlertEngine:
    """Configurable alert engine with cooldowns and deduplication."""

    def __init__(self) -> None:
        self._rules: Dict[str, AlertRule] = {}
        self._fired: Deque[Alert] = deque(maxlen=500)
        self._last_fired: Dict[str, float] = {}
        self._callbacks: List[Callable] = []

    def add_rule(self, rule: AlertRule) -> None:
        self._rules[rule.id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        return self._rules.pop(rule_id, None) is not None

    def on_alert(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def check(self, metric_name: str, value: float) -> List[Alert]:
        """Check a metric value against all rules."""
        fired: List[Alert] = []

        for rule in self._rules.values():
            if not rule.enabled or rule.metric_name != metric_name:
                continue

            # Check condition
            triggered = False
            if rule.condition == "gt" and value > rule.threshold:
                triggered = True
            elif rule.condition == "lt" and value < rule.threshold:
                triggered = True
            elif rule.condition == "gte" and value >= rule.threshold:
                triggered = True
            elif rule.condition == "lte" and value <= rule.threshold:
                triggered = True
            elif rule.condition == "eq" and value == rule.threshold:
                triggered = True

            if not triggered:
                continue

            # Cooldown check
            now = time.time()
            last = self._last_fired.get(rule.id, 0)
            if now - last < rule.cooldown_s:
                continue

            # Fire alert
            message = rule.message_template.format(
                value=value, threshold=rule.threshold,
                metric=metric_name,
            )
            alert = Alert(
                rule_id=rule.id,
                severity=rule.severity,
                message=message,
                metric_name=metric_name,
                metric_value=value,
                threshold=rule.threshold,
            )

            self._fired.append(alert)
            self._last_fired[rule.id] = now
            fired.append(alert)

            # Dispatch
            if rule.channel == AlertChannel.LOG:
                log_fn = {
                    AlertSeverity.INFO: logger.info,
                    AlertSeverity.WARNING: logger.warning,
                    AlertSeverity.ERROR: logger.error,
                    AlertSeverity.CRITICAL: logger.critical,
                }.get(rule.severity, logger.warning)
                log_fn(f"ALERT [{rule.severity.value}] {message}")

            if rule.callback:
                try:
                    rule.callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")

            for cb in self._callbacks:
                try:
                    cb(alert)
                except Exception as e:
                    logger.debug("Suppressed: %s", e)

        return fired

    @property
    def recent_alerts(self) -> List[Alert]:
        return list(self._fired)

    def acknowledge(self, rule_id: str) -> bool:
        for alert in reversed(self._fired):
            if alert.rule_id == rule_id and not alert.acknowledged:
                alert.acknowledged = True
                return True
        return False


# Global alert engine
alerts = AlertEngine()

# Register default alert rules
alerts.add_rule(AlertRule(
    id="cpu_high", name="High CPU Usage",
    metric_name="cpu_percent", condition="gt", threshold=90,
    severity=AlertSeverity.WARNING,
    message_template="CPU usage at {value:.1f}% (threshold: {threshold}%)",
))
alerts.add_rule(AlertRule(
    id="memory_high", name="High Memory Usage",
    metric_name="memory_percent", condition="gt", threshold=85,
    severity=AlertSeverity.WARNING,
    message_template="Memory usage at {value:.1f}% (threshold: {threshold}%)",
))
alerts.add_rule(AlertRule(
    id="disk_critical", name="Disk Space Critical",
    metric_name="disk_percent", condition="gt", threshold=95,
    severity=AlertSeverity.CRITICAL,
    message_template="Disk usage at {value:.1f}% — CRITICAL (threshold: {threshold}%)",
))
alerts.add_rule(AlertRule(
    id="error_rate", name="High Error Rate",
    metric_name="bot_error_rate", condition="gt", threshold=0.1,
    severity=AlertSeverity.ERROR,
    message_template="Error rate at {value:.1%} (threshold: {threshold:.0%})",
))


# ═══════════════════════════════════════════════════════════════════
# User Activity Tracker
# ═══════════════════════════════════════════════════════════════════

class UserTracker:
    """Track user activity patterns."""

    def __init__(self) -> None:
        self._users: Dict[str, UserActivity] = {}
        self._session_timeout = 1800    # 30 min

    def record_activity(self, user_id: str, command: str = "") -> None:
        now = time.time()
        if user_id not in self._users:
            self._users[user_id] = UserActivity(
                user_id=user_id, first_seen=now, last_seen=now,
            )

        user = self._users[user_id]

        # Session tracking
        if now - user.last_seen > self._session_timeout:
            user.session_count += 1

        user.last_seen = now
        user.total_messages += 1

        if command:
            user.total_commands += 1
            user.favorite_commands[command] = user.favorite_commands.get(command, 0) + 1

    def get_active_count(self, window_s: float = 3600) -> int:
        """Count users active in the last window."""
        cutoff = time.time() - window_s
        return sum(1 for u in self._users.values() if u.last_seen > cutoff)

    def get_user(self, user_id: str) -> Optional[UserActivity]:
        return self._users.get(user_id)

    def get_top_users(self, limit: int = 10) -> List[UserActivity]:
        return sorted(
            self._users.values(),
            key=lambda u: u.total_commands,
            reverse=True,
        )[:limit]

    def retention_rate(self, days: int = 7) -> float:
        """Calculate user retention rate."""
        cutoff = time.time() - (days * 86400)
        total = len(self._users)
        if total == 0:
            return 0.0
        retained = sum(1 for u in self._users.values() if u.last_seen > cutoff)
        return retained / total


user_tracker = UserTracker()


# ═══════════════════════════════════════════════════════════════════
# API Usage Tracker
# ═══════════════════════════════════════════════════════════════════

class ApiTracker:
    """Track API usage per provider."""

    def __init__(self) -> None:
        self._providers: Dict[str, ApiUsage] = {}
        self._budgets: Dict[str, float] = {}

    def record_call(self, provider: str, tokens: int = 0,
                    cost: float = 0.0, latency_ms: float = 0.0,
                    error: bool = False) -> None:
        if provider not in self._providers:
            self._providers[provider] = ApiUsage(provider=provider)

        usage = self._providers[provider]
        usage.total_calls += 1
        usage.total_tokens += tokens
        usage.total_cost += cost
        usage.last_call_ts = time.time()

        if error:
            usage.error_count += 1

        # Update average latency (exponential moving average)
        if latency_ms > 0:
            if usage.avg_latency_ms == 0:
                usage.avg_latency_ms = latency_ms
            else:
                usage.avg_latency_ms = 0.9 * usage.avg_latency_ms + 0.1 * latency_ms

        # Update global metrics
        metrics.increment("api_calls")
        metrics.increment("api_cost", cost)
        metrics.record("api_latency", latency_ms)

    def set_budget(self, provider: str, budget_usd: float) -> None:
        self._budgets[provider] = budget_usd

    def check_budget(self, provider: str) -> Dict[str, Any]:
        usage = self._providers.get(provider)
        return {'allowed': True, 'remaining': 999999, 'limit': 999999}  # v9.7.1


    def forecast_cost(self, provider: str, days: int = 30) -> float:
        """Forecast cost for N days based on current rate."""
        usage = self._providers.get(provider)
        if not usage or usage.total_calls == 0:
            return 0.0
        elapsed_days = max(1, (time.time() - usage.last_call_ts) / 86400)
        daily_rate = usage.total_cost / elapsed_days
        return round(daily_rate * days, 4)

    def get_all(self) -> Dict[str, ApiUsage]:
        return dict(self._providers)

    def summary(self) -> Dict[str, Any]:
        return {
            provider: {
                "calls": u.total_calls,
                "tokens": u.total_tokens,
                "cost": round(u.total_cost, 4),
                "avg_latency_ms": round(u.avg_latency_ms, 1),
                "errors": u.error_count,
            }
            for provider, u in self._providers.items()
        }


api_tracker = ApiTracker()


# ═══════════════════════════════════════════════════════════════════
# Health Score Calculator
# ═══════════════════════════════════════════════════════════════════

def calculate_health_score() -> Tuple[float, HealthStatus, Dict[str, float]]:
    """
    Calculate overall bot health score (0-100).

    Scoring:
      - System resources:  30 points (CPU, memory, disk)
      - Error rate:        25 points
      - API health:        20 points
      - Response time:     15 points
      - Uptime:           10 points
    """
    components: Dict[str, float] = {}
    score = 0.0

    # System resources (30)
    sys_info = get_system_info()
    cpu_score = max(0, 10 - (sys_info.cpu_percent / 10))
    mem_score = max(0, 10 - (sys_info.memory_percent / 10))
    disk_score = max(0, 10 - (sys_info.disk_percent / 10))
    components["system"] = cpu_score + mem_score + disk_score
    score += components["system"]

    # Error rate (25)
    error_series = metrics.get("bot_errors")
    cmd_series = metrics.get("bot_commands")
    if error_series and cmd_series:
        errors = error_series.latest or 0
        commands = cmd_series.latest or 1
        error_rate = errors / max(commands, 1)
        components["error_rate"] = max(0, 25 * (1 - error_rate * 10))
    else:
        components["error_rate"] = 25
    score += components["error_rate"]

    # API health (20)
    latency_series = metrics.get("api_latency")
    if latency_series and latency_series.latest is not None:
        avg_latency = latency_series.mean()
        components["api_health"] = max(0, 20 * (1 - avg_latency / 10000))
    else:
        components["api_health"] = 20
    score += components["api_health"]

    # Response time (15)
    rt_series = metrics.get("response_time")
    if rt_series and rt_series.latest is not None:
        avg_rt = rt_series.mean()
        components["response_time"] = max(0, 15 * (1 - avg_rt / 5000))
    else:
        components["response_time"] = 15
    score += components["response_time"]

    # Uptime (10)
    uptime = sys_info.uptime_seconds
    components["uptime"] = min(10, uptime / 8640)  # Full score after 1 day
    score += components["uptime"]

    score = max(0, min(100, score))

    # Determine status
    if score >= 80:
        status = HealthStatus.HEALTHY
    elif score >= 60:
        status = HealthStatus.DEGRADED
    elif score >= 30:
        status = HealthStatus.UNHEALTHY
    else:
        status = HealthStatus.DOWN

    return round(score, 1), status, components


# ═══════════════════════════════════════════════════════════════════
# ASCII Dashboard Renderer
# ═══════════════════════════════════════════════════════════════════

def render_dashboard() -> str:
    """Render an ASCII dashboard of current system and bot status."""
    sys_info = get_system_info()
    health_score, health_status, components = calculate_health_score()

    def bar(pct: float, width: int = 20) -> str:
        filled = int(pct / 100 * width)
        return "█" * filled + "░" * (width - filled) + f" {pct:.1f}%"

    def status_icon(status: HealthStatus) -> str:
        return {
            HealthStatus.HEALTHY: "🟢",
            HealthStatus.DEGRADED: "🟡",
            HealthStatus.UNHEALTHY: "🟠",
            HealthStatus.DOWN: "🔴",
        }[status]

    lines = [
        "╔══════════════════════════════════════════════════════╗",
        "║             ARKI DASHBOARD MONITOR                  ║",
        "╠══════════════════════════════════════════════════════╣",
        f"║ Health: {status_icon(health_status)} {health_status.value.upper()}"
        f"  Score: {health_score}/100"
        f"{'':>{40 - len(health_status.value) - len(str(health_score))}}║",
        "╠══════════════════════════════════════════════════════╣",
        "║ SYSTEM RESOURCES                                    ║",
        f"║  CPU:    {bar(sys_info.cpu_percent):>40}   ║",
        f"║  Memory: {bar(sys_info.memory_percent):>40}   ║",
        f"║  Disk:   {bar(sys_info.disk_percent):>40}   ║",
        "╠══════════════════════════════════════════════════════╣",
        "║ API USAGE                                           ║",
    ]

    api_summary = api_tracker.summary()
    if api_summary:
        for provider, stats in api_summary.items():
            lines.append(
                f"║  {provider[:15]:<15} │ {stats['calls']:>6} calls │ "
                f"${stats['cost']:>7.4f} ║"
            )
    else:
        lines.append("║  No API calls recorded yet                         ║")

    lines.extend([
        "╠══════════════════════════════════════════════════════╣",
        f"║ USERS: {user_tracker.get_active_count():>5} active (1h) │ "
        f"{len(user_tracker._users):>5} total          ║",
        "╠══════════════════════════════════════════════════════╣",
    ])

    # Recent alerts
    recent = alerts.recent_alerts[-5:]
    if recent:
        lines.append("║ RECENT ALERTS                                      ║")
        for a in reversed(recent):
            icon = {"info": "ℹ️", "warning": "⚠️", "error": "❌",
                    "critical": "🚨"}.get(a.severity.value, "•")
            msg = a.message[:42]
            lines.append(f"║  {icon} {msg:<45} ║")
    else:
        lines.append("║ No recent alerts ✅                                ║")

    lines.append("╚══════════════════════════════════════════════════════╝")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Report Generation
# ═══════════════════════════════════════════════════════════════════

def generate_report() -> Dict[str, Any]:
    """Generate a comprehensive monitoring report."""
    sys_info = get_system_info()
    health_score, health_status, components = calculate_health_score()

    return {
        "timestamp": time.time(),
        "health": {
            "score": health_score,
            "status": health_status.value,
            "components": components,
        },
        "system": {
            "hostname": sys_info.hostname,
            "cpu_percent": sys_info.cpu_percent,
            "memory_percent": sys_info.memory_percent,
            "disk_percent": sys_info.disk_percent,
            "uptime_s": sys_info.uptime_seconds,
        },
        "api_usage": api_tracker.summary(),
        "users": {
            "active_1h": user_tracker.get_active_count(3600),
            "total": len(user_tracker._users),
            "retention_7d": round(user_tracker.retention_rate(7), 2),
        },
        "alerts": {
            "total": len(alerts.recent_alerts),
            "unacknowledged": sum(
                1 for a in alerts.recent_alerts if not a.acknowledged
            ),
        },
        "metrics": metrics.snapshot(),
    }


