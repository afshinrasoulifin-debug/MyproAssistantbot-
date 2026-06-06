
"""
platform_auto_pkg — modular version of platform_auto.py
Arki Engine v30
"""
from __future__ import annotations

try:
    from .base import *  # noqa: F401,F403
except Exception:
    pass
try:
    from .cb_pipeline_group import *  # noqa: F401,F403
except Exception:
    pass
try:
    from .cmd_templates_group import *  # noqa: F401,F403
except Exception:
    pass

__all__ = ['cmd_addproduct', 'cmd_products', 'cmd_editproduct', 'cmd_delproduct', 'cmd_autopipeline', 'cb_pipeline', 'cb_photos', 'cb_captions', 'cb_listings', 'cb_view_product', 'cmd_queue', 'cb_queue_done', 'cmd_postqueue', 'cmd_sales', 'cmd_dashboard', 'cmd_weeklytasks', 'cmd_templates']


