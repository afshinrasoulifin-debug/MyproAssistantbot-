
"""
router_pkg — modular version of router.py
Arki Engine v30
"""
from __future__ import annotations

try:
    from .base import *  # noqa: F401,F403
except Exception:
    pass
try:
    from .cmd_consortium_group import *  # noqa: F401,F403
except Exception:
    pass
try:
    from .cmd_libertas_group import *  # noqa: F401,F403
except Exception:
    pass

__all__ = ['get_apex_prompt', 'apply_stm_to_response', 'cmd_extra', 'cb_extra_menu', 'cmd_apex', 'cb_apex', 'cb_apex_toggle', 'cmd_race', 'cb_race_info', 'cmd_consortium', 'cb_consortium_info', 'cmd_chat', 'cb_chat_info', 'cmd_parseltongue', 'cb_parseltongue_info', 'cmd_autotune_pro', 'cb_autotune_info', 'cmd_stm', 'cb_stm', 'cb_stm_toggle', 'cmd_libertas', 'cb_libertas_info', 'cb_feedback_info', 'cmd_feedback', 'cmd_g0dstatus', 'cb_status', 'cb_status_group', 'cmd_classify']


