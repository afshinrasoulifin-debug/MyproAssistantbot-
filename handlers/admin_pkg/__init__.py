
"""
admin_pkg — modular version of admin.py
Arki Engine v29.0.0
"""
from __future__ import annotations
try:
    from ._common import router  # noqa: F401
except Exception:
    pass

try:
    from . import base  # noqa: F401
except Exception:
    pass
try:
    from . import _ban  # noqa: F401
except Exception:
    pass
try:
    from . import _unban  # noqa: F401
except Exception:
    pass
try:
    from . import _stats  # noqa: F401
except Exception:
    pass
try:
    from . import _users  # noqa: F401
except Exception:
    pass
try:
    from . import _broadcast_new  # noqa: F401
except Exception:
    pass
try:
    from . import _health_new  # noqa: F401
except Exception:
    pass
try:
    from . import _analytics_new  # noqa: F401
except Exception:
    pass
try:
    from . import _maintenance_new  # noqa: F401
except Exception:
    pass
try:
    from . import _backup_db_new  # noqa: F401
except Exception:
    pass
try:
    from . import helpers  # noqa: F401
except Exception:
    pass


