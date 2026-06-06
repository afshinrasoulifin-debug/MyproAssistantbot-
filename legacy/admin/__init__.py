
"""
admin/ — Arki Engine Web Admin Panel v27.0
═══════════════════════════════════════════
Provides a web-based admin dashboard for monitoring and managing
the Arki Engine bot. Serves at /admin/ via the main aiohttp app.

Features:
  - Real-time model health dashboard
  - Circuit breaker status viewer
  - User statistics
  - Performance metrics
  - Log viewer
  - Model management
"""
from admin.dashboard import setup_admin_routes

__all__ = ["setup_admin_routes"]


