
"""
agents_pkg — modular version of agents.py
Arki Engine v30
"""
from __future__ import annotations

try:
    from .base import *  # noqa: F401,F403
except Exception:
    pass
try:
    from .cmd_finance_group import *  # noqa: F401,F403
except Exception:
    pass
try:
    from .cmd_plan_group import *  # noqa: F401,F403
except Exception:
    pass

__all__ = ['cmd_agents', 'cb_agent_help', 'cmd_workflow', 'cmd_crm', 'cmd_finance', 'cmd_monitor', 'cmd_autoreply', 'cmd_plan', 'start_monitor_bg', 'cmd_agent']


