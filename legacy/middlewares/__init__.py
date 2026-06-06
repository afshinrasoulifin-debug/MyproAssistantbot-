
"""
tg_bot/middlewares — Request processing pipeline.

Order matters:
  1. MaintenanceMiddleware — block all if maintenance mode
  2. RateLimiterMiddleware — prevent spam
  3. AutoRegisterMiddleware — register/lookup user
  4. AnalyticsMiddleware — track usage (innermost)
"""


