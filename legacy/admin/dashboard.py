
from __future__ import annotations
"""
admin/dashboard.py — Admin Dashboard v29.0
═══════════════════════════════════════════
Real admin panel with:
  - API-token based auth
  - User management (list, ban, set tier)
  - Victor brain stats
  - Rate limiter stats
  - System metrics
  - Circuit breakers & health
"""

import logging
import os
import time
from typing import Any, Dict

from aiohttp import web

logger = logging.getLogger(__name__)

# ── Auth ──────────────────────────────────────────────
# Admin token from environment — must be set for production
_ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")


def _check_auth(request: web.Request) -> bool:
    """Check admin token from query param or header."""
    if not _ADMIN_TOKEN:
        # No token configured → allow all (dev mode)
        return True
    token = request.query.get("token", "")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    return token == _ADMIN_TOKEN


def _auth_required(handler: Any) -> Any:
    """Decorator for admin auth."""
    async def wrapper(request: web.Request) -> web.Response:
        if not _check_auth(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        return await handler(request)
    return wrapper


# ── Route setup ───────────────────────────────────────

def setup_admin_routes(app: web.Application) -> None:
    """Register all admin routes on the aiohttp app."""
    app.router.add_get("/admin", admin_dashboard)
    app.router.add_get("/admin/", admin_dashboard)

    # API endpoints (all auth-protected)
    app.router.add_get("/admin/api/overview", _auth_required(api_overview))
    app.router.add_get("/admin/api/models", _auth_required(api_models))
    app.router.add_get("/admin/api/health", _auth_required(api_health))
    app.router.add_get("/admin/api/circuit-breakers", _auth_required(api_circuit_breakers))
    app.router.add_get("/admin/api/stats", _auth_required(api_stats))
    app.router.add_get("/admin/api/connections", _auth_required(api_connections))
    app.router.add_get("/admin/api/memory", _auth_required(api_memory))
    app.router.add_get("/admin/api/users", _auth_required(api_users))
    app.router.add_post("/admin/api/users/{user_id}/ban", _auth_required(api_ban_user))
    app.router.add_post("/admin/api/users/{user_id}/unban", _auth_required(api_unban_user))
    app.router.add_post("/admin/api/users/{user_id}/tier", _auth_required(api_set_tier))
    app.router.add_get("/admin/api/brain", _auth_required(api_brain_stats))
    app.router.add_get("/admin/api/rate-limits", _auth_required(api_rate_limits))

    logger.info("Admin dashboard routes registered at /admin/ (%s)",
                 "auth required" if _ADMIN_TOKEN else "NO AUTH — dev mode")


# ── API Endpoints ─────────────────────────────────────

async def admin_dashboard(request: web.Request) -> web.Response:
    """Serve the main admin dashboard HTML."""
    return web.Response(text=_DASHBOARD_HTML, content_type="text/html")


async def api_overview(request: web.Request) -> web.Response:
    """API: System overview."""
    try:
        import platform
        data = {
            "version": _read_version(),
            "python": platform.python_version(),
            "platform": platform.system(),
            "uptime_seconds": _get_uptime(),
            "timestamp": time.time(),
        }
        try:
            from utils.metrics_collector import get_metrics
            m = get_metrics()
            all_m = m.get_all()
            data["metrics"] = {
                "uptime": all_m.get("uptime_seconds", 0),
                "counters": all_m.get("counters", {}),
            }
        except Exception:
            pass
        return web.json_response(data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def api_models(request: web.Request) -> web.Response:
    """API: Get all model information."""
    try:
        from utils.models_registry import MODELS, APEX_TIERS
        data = {
            "base_models": len(MODELS),
            "apex_tiers": {},
            "total": len(MODELS),
        }
        for tier, models in APEX_TIERS.items():
            data["apex_tiers"][tier] = {
                "count": len(models),
                "models": [
                    {"key": k, "model_id": m.model_id, "display_name": m.display_name}
                    for k, m in models.items()
                ],
            }
            data["total"] += len(models)
        return web.json_response(data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def api_health(request: web.Request) -> web.Response:
    """API: Get provider health status."""
    try:
        from utils.resilience import get_health_monitor
        monitor = get_health_monitor()
        return web.json_response({
            "providers": monitor.get_all_health(),
            "timestamp": time.time(),
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def api_circuit_breakers(request: web.Request) -> web.Response:
    """API: Get circuit breaker status."""
    try:
        from utils.resilience import get_circuit_manager
        manager = get_circuit_manager()
        return web.json_response({
            "breakers": manager.get_all_stats(),
            "healthy_providers": list(manager.get_healthy_providers()),
            "timestamp": time.time(),
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def api_stats(request: web.Request) -> web.Response:
    """API: Get performance statistics."""
    try:
        from utils.performance_analytics import _state
        stats = {
            "total_requests": getattr(_state, 'total_requests', 0),
            "total_successes": getattr(_state, 'total_successes', 0),
            "total_failures": getattr(_state, 'total_failures', 0),
            "uptime": time.time() - getattr(_state, 'start_time', time.time()),
        }
        return web.json_response(stats)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def api_connections(request: web.Request) -> web.Response:
    """API: Get connection pool stats."""
    try:
        from utils.resilience import get_connection_pool
        pool = get_connection_pool()
        return web.json_response(pool.get_stats())
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def api_memory(request: web.Request) -> web.Response:
    """API: Get memory guard stats."""
    try:
        from utils.resilience import get_memory_guard
        guard = get_memory_guard()
        try:
            import psutil
            proc = psutil.Process()
            mem = proc.memory_info()
            return web.json_response({
                "guard": guard.get_stats(),
                "process_rss_mb": round(mem.rss / 1024 / 1024, 1),
                "process_vms_mb": round(mem.vms / 1024 / 1024, 1),
            })
        except ImportError:
            return web.json_response({"guard": guard.get_stats()})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def api_users(request: web.Request) -> web.Response:
    """API: List users with pagination."""
    try:
        from database.connection import get_session
        from sqlalchemy import text

        page = int(request.query.get("page", 1))
        per_page = min(int(request.query.get("per_page", 50)), 100)
        offset = (page - 1) * per_page
        search = request.query.get("search", "")

        async with get_session() as session:
            # Count total
            if search:
                count_q = text(
                    "SELECT COUNT(*) FROM users WHERE "
                    "CAST(telegram_id AS TEXT) LIKE :s OR "
                    "username LIKE :s OR full_name LIKE :s"
                )
                total = (await session.execute(count_q, {"s": f"%{search}%"})).scalar()
            else:
                total = (await session.execute(text("SELECT COUNT(*) FROM users"))).scalar()

            # Fetch page
            if search:
                query = text(
                    "SELECT telegram_id, username, full_name, language, "
                    "is_banned, is_premium, message_count, tier, created_at, last_active "
                    "FROM users WHERE "
                    "CAST(telegram_id AS TEXT) LIKE :s OR "
                    "username LIKE :s OR full_name LIKE :s "
                    "ORDER BY last_active DESC NULLS LAST "
                    "LIMIT :limit OFFSET :offset"
                )
                rows = (await session.execute(
                    query, {"s": f"%{search}%", "limit": per_page, "offset": offset}
                )).fetchall()
            else:
                query = text(
                    "SELECT telegram_id, username, full_name, language, "
                    "is_banned, is_premium, message_count, tier, created_at, last_active "
                    "FROM users ORDER BY last_active DESC NULLS LAST "
                    "LIMIT :limit OFFSET :offset"
                )
                rows = (await session.execute(
                    query, {"limit": per_page, "offset": offset}
                )).fetchall()

            users = []
            for row in rows:
                users.append({
                    "telegram_id": row[0],
                    "username": row[1],
                    "full_name": row[2],
                    "language": row[3],
                    "is_banned": bool(row[4]),
                    "is_premium": bool(row[5]),
                    "message_count": row[6],
                    "tier": row[7] or "free",
                    "created_at": str(row[8]) if row[8] else None,
                    "last_active": str(row[9]) if row[9] else None,
                })

        return web.json_response({
            "users": users,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page if total else 0,
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def api_ban_user(request: web.Request) -> web.Response:
    """API: Ban a user."""
    try:
        user_id = int(request.match_info["user_id"])
        from database.connection import get_session
        from sqlalchemy import text
        async with get_session() as session:
            await session.execute(
                text("UPDATE users SET is_banned = 1 WHERE telegram_id = :uid"),
                {"uid": user_id},
            )
            await session.commit()
        logger.info("Admin: banned user %d", user_id)
        return web.json_response({"status": "banned", "user_id": user_id})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def api_unban_user(request: web.Request) -> web.Response:
    """API: Unban a user."""
    try:
        user_id = int(request.match_info["user_id"])
        from database.connection import get_session
        from sqlalchemy import text
        async with get_session() as session:
            await session.execute(
                text("UPDATE users SET is_banned = 0 WHERE telegram_id = :uid"),
                {"uid": user_id},
            )
            await session.commit()
        logger.info("Admin: unbanned user %d", user_id)
        return web.json_response({"status": "unbanned", "user_id": user_id})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def api_set_tier(request: web.Request) -> web.Response:
    """API: Set user tier."""
    try:
        user_id = int(request.match_info["user_id"])
        body = await request.json()
        tier = body.get("tier", "free")
        valid_tiers = ["free", "pro", "enterprise", "unlimited"]
        if tier not in valid_tiers:
            return web.json_response(
                {"error": f"Invalid tier. Must be one of: {valid_tiers}"}, status=400
            )

        from database.connection import get_session
        from sqlalchemy import text
        async with get_session() as session:
            await session.execute(
                text("UPDATE users SET tier = :tier WHERE telegram_id = :uid"),
                {"tier": tier, "uid": user_id},
            )
            await session.commit()

        # Update in-memory cache
        from middlewares.rate_limiter import set_user_tier, UserTier
        set_user_tier(user_id, UserTier(tier))

        logger.info("Admin: set user %d tier to %s", user_id, tier)
        return web.json_response({"status": "updated", "user_id": user_id, "tier": tier})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def api_brain_stats(request: web.Request) -> web.Response:
    """API: Get Victor brain statistics."""
    try:
        import pathlib
        brain_dir = pathlib.Path("data/brain")
        if not brain_dir.exists():
            brain_dir = pathlib.Path("brain_data")

        stats: Dict[str, Any] = {"available": False}

        # Try to read memory stats
        memories_file = brain_dir / "memories.json"
        if memories_file.exists():
            import json as _json
            data = _json.loads(memories_file.read_text(encoding="utf-8"))
            stats["available"] = True
            stats["total_memories"] = len(data) if isinstance(data, (list, dict)) else 0

        # Try to read graph stats
        graph_file = brain_dir / "graph.json"
        if graph_file.exists():
            data = _json.loads(graph_file.read_text(encoding="utf-8"))
            stats["graph_edges"] = len(data) if isinstance(data, (list, dict)) else 0

        # Try to read patterns
        patterns_file = brain_dir / "patterns.json"
        if patterns_file.exists():
            data = _json.loads(patterns_file.read_text(encoding="utf-8"))
            stats["patterns"] = len(data) if isinstance(data, (list, dict)) else 0

        # Try to read config
        config_file = brain_dir / "config.json"
        if config_file.exists():
            stats["config"] = _json.loads(config_file.read_text(encoding="utf-8"))

        return web.json_response(stats)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def api_rate_limits(request: web.Request) -> web.Response:
    """API: Get rate limiter statistics."""
    try:
        from middlewares.rate_limiter import (
            TIER_LIMITS, ENDPOINT_LIMITS, _user_tiers,
        )
        data = {
            "tier_limits": {t.value: limits for t, limits in TIER_LIMITS.items()},
            "endpoint_limits": {
                ep: {t.value: lim for t, lim in tiers.items()}
                for ep, tiers in ENDPOINT_LIMITS.items()
            },
            "cached_tiers": {
                str(uid): tier.value for uid, tier in _user_tiers.items()
            },
            "total_cached": len(_user_tiers),
        }
        return web.json_response(data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ── Helpers ───────────────────────────────────────────

_start_time = time.time()

def _get_uptime() -> float:
    return time.time() - _start_time

def _read_version() -> str:
    try:
        return open("VERSION").read().strip()
    except Exception:
        return "unknown"


# ═══════════════════════════════════════════════════════════════════
# Dashboard HTML v29.0 — Full admin panel
# ═══════════════════════════════════════════════════════════════════

_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Arki Engine v29 — Admin Panel</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0a0f;--card:#12121a;--border:#1e1e2e;--accent:#6c5ce7;
--green:#00b894;--red:#e74c3c;--yellow:#fdcb6e;--text:#dfe6e9;--dim:#636e72;
--hover:#1a1a2e}
body{font-family:'Segoe UI',Tahoma,sans-serif;background:var(--bg);color:var(--text);
min-height:100vh;direction:rtl}
.header{background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
padding:20px 30px;border-bottom:1px solid var(--border);display:flex;
align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px}
.header h1{font-size:1.4em;background:linear-gradient(90deg,var(--accent),#a29bfe);
-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header .ver{color:var(--dim);font-size:0.85em}
.nav{display:flex;gap:8px;padding:10px 30px;border-bottom:1px solid var(--border);
background:#0e0e16;flex-wrap:wrap}
.nav button{background:var(--card);color:var(--text);border:1px solid var(--border);
padding:8px 16px;border-radius:8px;cursor:pointer;font-size:0.85em;transition:all 0.2s}
.nav button:hover{background:var(--hover)}
.nav button.active{background:var(--accent);border-color:var(--accent);color:#fff}
.panel{display:none;padding:20px 30px}
.panel.active{display:block}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;
padding:20px;transition:transform 0.2s}
.card:hover{transform:translateY(-2px)}
.card h2{font-size:1.05em;color:var(--accent);margin-bottom:12px;
border-bottom:1px solid var(--border);padding-bottom:8px}
.stat{display:flex;justify-content:space-between;padding:6px 0;
border-bottom:1px solid rgba(255,255,255,0.05)}
.stat .label{color:var(--dim)}
.stat .value{font-weight:600;font-variant-numeric:tabular-nums}
.healthy{color:var(--green)}.unhealthy{color:var(--red)}.warning{color:var(--yellow)}
.badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:0.8em;font-weight:600}
.badge.free{background:rgba(99,110,114,0.2);color:var(--dim)}
.badge.pro{background:rgba(108,92,231,0.2);color:var(--accent)}
.badge.enterprise{background:rgba(253,203,110,0.2);color:var(--yellow)}
.badge.unlimited{background:rgba(0,184,148,0.2);color:var(--green)}
.badge.banned{background:rgba(231,76,60,0.2);color:var(--red)}
table{width:100%;border-collapse:collapse;font-size:0.9em}
th{text-align:right;padding:8px;color:var(--accent);border-bottom:2px solid var(--border)}
td{padding:6px 8px;border-bottom:1px solid rgba(255,255,255,0.03)}
tr:hover td{background:rgba(108,92,231,0.05)}
.btn{padding:4px 12px;border-radius:6px;border:none;cursor:pointer;font-size:0.8em;
transition:opacity 0.2s}
.btn:hover{opacity:0.8}
.btn-danger{background:var(--red);color:#fff}
.btn-success{background:var(--green);color:#fff}
.btn-primary{background:var(--accent);color:#fff}
.search-box{background:var(--card);border:1px solid var(--border);color:var(--text);
padding:10px 16px;border-radius:8px;width:100%;max-width:400px;margin-bottom:16px;
font-size:0.9em}
.search-box:focus{outline:none;border-color:var(--accent)}
select{background:var(--card);border:1px solid var(--border);color:var(--text);
padding:4px 8px;border-radius:6px;font-size:0.8em}
.pagination{display:flex;gap:8px;margin-top:16px;justify-content:center}
.pagination button{background:var(--card);border:1px solid var(--border);color:var(--text);
padding:6px 14px;border-radius:6px;cursor:pointer}
.pagination button.active{background:var(--accent);border-color:var(--accent)}
.last-update{color:var(--dim);font-size:0.8em;text-align:center;padding:10px}
.refresh{background:var(--accent);color:#fff;border:none;padding:8px 20px;
border-radius:8px;cursor:pointer;font-size:0.9em}
.refresh:hover{opacity:0.8}
@media(max-width:768px){.header{padding:15px}.grid{grid-template-columns:1fr}
.nav{overflow-x:auto}.panel{padding:15px}}
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>⚡ Arki Engine — Admin Panel</h1>
    <span class="ver">v29.0 TITANIUM</span>
  </div>
  <button class="refresh" onclick="refreshCurrent()">🔄 بروزرسانی</button>
</div>

<div class="nav" id="nav">
  <button class="active" onclick="showPanel('overview')">📊 نمای کلی</button>
  <button onclick="showPanel('users')">👥 کاربران</button>
  <button onclick="showPanel('brain')">🧠 Victor Brain</button>
  <button onclick="showPanel('infra')">🔧 زیرساخت</button>
  <button onclick="showPanel('ratelimit')">⏱️ Rate Limits</button>
</div>

<!-- Overview Panel -->
<div class="panel active" id="panel-overview">
  <div class="grid">
    <div class="card"><h2>📊 وضعیت سیستم</h2><div id="overview-system"><em>بارگذاری...</em></div></div>
    <div class="card"><h2>📈 عملکرد</h2><div id="overview-stats"><em>بارگذاری...</em></div></div>
    <div class="card"><h2>🤖 مدل‌ها</h2><div id="overview-models"><em>بارگذاری...</em></div></div>
    <div class="card"><h2>⚡ Circuit Breakers</h2><div id="overview-breakers"><em>بارگذاری...</em></div></div>
    <div class="card"><h2>❤️ سلامت</h2><div id="overview-health"><em>بارگذاری...</em></div></div>
    <div class="card"><h2>💾 حافظه</h2><div id="overview-memory"><em>بارگذاری...</em></div></div>
  </div>
</div>

<!-- Users Panel -->
<div class="panel" id="panel-users">
  <input type="text" class="search-box" id="user-search" placeholder="🔍 جستجوی کاربر (نام، آیدی...)" oninput="searchUsers()">
  <div id="users-content"><em>بارگذاری...</em></div>
</div>

<!-- Brain Panel -->
<div class="panel" id="panel-brain">
  <div class="grid">
    <div class="card"><h2>🧠 آمار حافظه Victor</h2><div id="brain-stats"><em>بارگذاری...</em></div></div>
    <div class="card"><h2>📚 پایگاه دانش</h2><div id="brain-knowledge"><em>بارگذاری...</em></div></div>
  </div>
</div>

<!-- Infrastructure Panel -->
<div class="panel" id="panel-infra">
  <div class="grid">
    <div class="card"><h2>🔌 اتصالات</h2><div id="infra-connections"><em>بارگذاری...</em></div></div>
    <div class="card"><h2>⚡ Circuit Breakers</h2><div id="infra-breakers"><em>بارگذاری...</em></div></div>
    <div class="card"><h2>❤️ Health</h2><div id="infra-health"><em>بارگذاری...</em></div></div>
  </div>
</div>

<!-- Rate Limit Panel -->
<div class="panel" id="panel-ratelimit">
  <div class="grid">
    <div class="card"><h2>⏱️ محدودیت‌های هر سطح</h2><div id="rl-tiers"><em>بارگذاری...</em></div></div>
    <div class="card"><h2>🎯 محدودیت هر Endpoint</h2><div id="rl-endpoints"><em>بارگذاری...</em></div></div>
    <div class="card"><h2>👤 سطح‌بندی فعلی</h2><div id="rl-cached"><em>بارگذاری...</em></div></div>
  </div>
</div>

<div class="last-update" id="last-update"></div>

<script>
const API = '/admin/api';
const token = new URLSearchParams(window.location.search).get('token') || '';
const authQ = token ? '?token='+encodeURIComponent(token) : '';
let currentPanel = 'overview';
let usersPage = 1;

async function fetchJ(url) {
  try {
    const sep = url.includes('?') ? '&' : '?';
    const r = await fetch(url + (token ? sep+'token='+encodeURIComponent(token) : ''));
    if (r.status === 401) return {error:'احراز هویت ناموفق — token نامعتبر'};
    if (!r.ok) return {error: r.statusText};
    return await r.json();
  } catch(e) { return {error: e.message}; }
}

function stat(l,v,c=''){return `<div class="stat"><span class="label">${l}</span><span class="value ${c}">${v}</span></div>`}

function showPanel(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
  document.getElementById('panel-'+name).classList.add('active');
  document.querySelectorAll('.nav button')[
    ['overview','users','brain','infra','ratelimit'].indexOf(name)
  ].classList.add('active');
  currentPanel = name;
  refreshCurrent();
}

async function refreshCurrent() {
  const loaders = {
    overview: loadOverview,
    users: () => loadUsers(usersPage),
    brain: loadBrain,
    infra: loadInfra,
    ratelimit: loadRateLimits,
  };
  await (loaders[currentPanel] || loadOverview)();
  document.getElementById('last-update').textContent =
    'آخرین بروزرسانی: ' + new Date().toLocaleTimeString('fa-IR');
}

async function loadOverview() {
  // System overview
  const ov = await fetchJ(API+'/overview');
  document.getElementById('overview-system').innerHTML = ov.error
    ? `<em>${ov.error}</em>`
    : stat('نسخه', ov.version) + stat('پایتون', ov.python) +
      stat('آپتایم', Math.floor(ov.uptime_seconds/3600)+' ساعت');

  // Stats
  const st = await fetchJ(API+'/stats');
  document.getElementById('overview-stats').innerHTML = st.error
    ? `<em>${st.error}</em>`
    : stat('درخواست‌ها', st.total_requests||0) +
      stat('موفق', st.total_successes||0, 'healthy') +
      stat('خطا', st.total_failures||0, 'unhealthy');

  // Models
  const md = await fetchJ(API+'/models');
  document.getElementById('overview-models').innerHTML = md.error
    ? `<em>${md.error}</em>`
    : stat('کل مدل‌ها', md.total||0);

  // Breakers
  const br = await fetchJ(API+'/circuit-breakers');
  if (br.error) {
    document.getElementById('overview-breakers').innerHTML = `<em>${br.error}</em>`;
  } else if (!br.breakers || br.breakers.length===0) {
    document.getElementById('overview-breakers').innerHTML = '<em>بدون Circuit Breaker</em>';
  } else {
    let h = '';
    for (const b of br.breakers)
      h += stat(b.provider, `<span class="badge ${b.state}">${b.state}</span>`);
    document.getElementById('overview-breakers').innerHTML = h;
  }

  // Health
  const hl = await fetchJ(API+'/health');
  if (hl.error || !hl.providers) {
    document.getElementById('overview-health').innerHTML = `<em>${hl.error||'بدون داده'}</em>`;
  } else {
    let h = '';
    for (const p of hl.providers)
      h += stat(p.provider, p.healthy?'✅':'❌', p.healthy?'healthy':'unhealthy');
    document.getElementById('overview-health').innerHTML = h;
  }

  // Memory
  const mm = await fetchJ(API+'/memory');
  document.getElementById('overview-memory').innerHTML = mm.error
    ? `<em>${mm.error}</em>`
    : stat('RSS', (mm.process_rss_mb||'?')+' MB') +
      stat('VMS', (mm.process_vms_mb||'?')+' MB');
}

async function loadUsers(page=1) {
  usersPage = page;
  const search = document.getElementById('user-search')?.value || '';
  const url = `${API}/users?page=${page}&per_page=20` + (search ? `&search=${encodeURIComponent(search)}` : '');
  const d = await fetchJ(url);
  if (d.error) { document.getElementById('users-content').innerHTML = `<em>${d.error}</em>`; return; }

  let html = `<table><tr><th>آیدی تلگرام</th><th>نام</th><th>پیام‌ها</th><th>سطح</th><th>وضعیت</th><th>عملیات</th></tr>`;
  for (const u of (d.users||[])) {
    const tierBadge = `<span class="badge ${u.tier}">${u.tier}</span>`;
    const banBadge = u.is_banned ? '<span class="badge banned">مسدود</span>' : '<span class="healthy">فعال</span>';
    const banBtn = u.is_banned
      ? `<button class="btn btn-success" onclick="unbanUser(${u.telegram_id})">رفع مسدود</button>`
      : `<button class="btn btn-danger" onclick="banUser(${u.telegram_id})">مسدود</button>`;
    const tierSelect = `<select onchange="setTier(${u.telegram_id}, this.value)">
      ${['free','pro','enterprise','unlimited'].map(t =>
        `<option value="${t}" ${t===u.tier?'selected':''}>${t}</option>`
      ).join('')}</select>`;
    html += `<tr>
      <td>${u.telegram_id}</td>
      <td>${u.full_name||''} ${u.username?'@'+u.username:''}</td>
      <td>${u.message_count}</td>
      <td>${tierBadge} ${tierSelect}</td>
      <td>${banBadge}</td>
      <td>${banBtn}</td>
    </tr>`;
  }
  html += '</table>';

  // Pagination
  if (d.pages > 1) {
    html += '<div class="pagination">';
    for (let i=1; i<=Math.min(d.pages,10); i++)
      html += `<button class="${i===page?'active':''}" onclick="loadUsers(${i})">${i}</button>`;
    if (d.pages > 10) html += `<span>... ${d.pages}</span>`;
    html += '</div>';
  }
  html += `<div style="color:var(--dim);margin-top:8px;font-size:0.85em">${d.total} کاربر</div>`;
  document.getElementById('users-content').innerHTML = html;
}

function searchUsers() { clearTimeout(window._st); window._st = setTimeout(()=>loadUsers(1), 300); }

async function banUser(uid) {
  if (!confirm('مسدود کردن کاربر '+uid+'؟')) return;
  await fetch(`${API}/users/${uid}/ban`+(token?'?token='+token:''), {method:'POST'});
  loadUsers(usersPage);
}
async function unbanUser(uid) {
  await fetch(`${API}/users/${uid}/unban`+(token?'?token='+token:''), {method:'POST'});
  loadUsers(usersPage);
}
async function setTier(uid, tier) {
  await fetch(`${API}/users/${uid}/tier`+(token?'?token='+token:''), {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({tier})
  });
  loadUsers(usersPage);
}

async function loadBrain() {
  const d = await fetchJ(API+'/brain');
  if (d.error) {
    document.getElementById('brain-stats').innerHTML = `<em>${d.error}</em>`;
    document.getElementById('brain-knowledge').innerHTML = '';
    return;
  }
  let h = stat('وضعیت', d.available?'✅ فعال':'❌ غیرفعال', d.available?'healthy':'unhealthy');
  if (d.total_memories !== undefined) h += stat('خاطرات', d.total_memories);
  if (d.graph_edges !== undefined) h += stat('یال‌های گراف', d.graph_edges);
  if (d.patterns !== undefined) h += stat('الگوها', d.patterns);
  document.getElementById('brain-stats').innerHTML = h;

  let k = '';
  if (d.config) {
    for (const [key, val] of Object.entries(d.config))
      k += stat(key, typeof val === 'object' ? JSON.stringify(val) : String(val));
  }
  document.getElementById('brain-knowledge').innerHTML = k || '<em>بدون تنظیمات</em>';
}

async function loadInfra() {
  const cn = await fetchJ(API+'/connections');
  document.getElementById('infra-connections').innerHTML = cn.error
    ? `<em>${cn.error}</em>`
    : Object.entries(cn).map(([k,v]) =>
        stat(k, typeof v==='object'?JSON.stringify(v):v)
      ).join('') || '<em>بدون اتصال</em>';

  const br = await fetchJ(API+'/circuit-breakers');
  if (br.error || !br.breakers?.length) {
    document.getElementById('infra-breakers').innerHTML = `<em>${br.error||'بدون CB'}</em>`;
  } else {
    let h = '<table><tr><th>Provider</th><th>State</th><th>Failures</th><th>Successes</th></tr>';
    for (const b of br.breakers)
      h += `<tr><td>${b.provider}</td><td><span class="badge ${b.state}">${b.state}</span></td>
            <td class="unhealthy">${b.total_failures}</td><td class="healthy">${b.total_successes}</td></tr>`;
    h += '</table>';
    document.getElementById('infra-breakers').innerHTML = h;
  }

  const hl = await fetchJ(API+'/health');
  if (hl.error || !hl.providers?.length) {
    document.getElementById('infra-health').innerHTML = `<em>${hl.error||'بدون داده'}</em>`;
  } else {
    let h = '';
    for (const p of hl.providers)
      h += stat(p.provider, (p.healthy?'✅':'❌')+' '+((p.latency_ms||'?')+' ms'),
                p.healthy?'healthy':'unhealthy');
    document.getElementById('infra-health').innerHTML = h;
  }
}

async function loadRateLimits() {
  const d = await fetchJ(API+'/rate-limits');
  if (d.error) {
    document.getElementById('rl-tiers').innerHTML = `<em>${d.error}</em>`;
    return;
  }
  // Tier limits
  let h = '<table><tr><th>سطح</th><th>درخواست/دقیقه</th><th>روزانه</th></tr>';
  for (const [tier, limits] of Object.entries(d.tier_limits||{}))
    h += `<tr><td><span class="badge ${tier}">${tier}</span></td>
          <td>${limits.requests_per_min}</td><td>${limits.daily_limit}</td></tr>`;
  h += '</table>';
  document.getElementById('rl-tiers').innerHTML = h;

  // Endpoint limits
  let e = '<table><tr><th>Endpoint</th><th>Free</th><th>Pro</th><th>Enterprise</th></tr>';
  for (const [ep, tiers] of Object.entries(d.endpoint_limits||{}))
    e += `<tr><td>/${ep}</td><td>${tiers.free||'-'}</td><td>${tiers.pro||'-'}</td><td>${tiers.enterprise||'-'}</td></tr>`;
  e += '</table>';
  document.getElementById('rl-endpoints').innerHTML = e;

  // Cached tiers
  let c = stat('کاربران cached', d.total_cached||0);
  for (const [uid, tier] of Object.entries(d.cached_tiers||{}))
    c += stat(uid, `<span class="badge ${tier}">${tier}</span>`);
  document.getElementById('rl-cached').innerHTML = c;
}

// Initial load
refreshCurrent();
setInterval(refreshCurrent, 30000);
</script>
</body>
</html>
"""


