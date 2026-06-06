
"""
web_search_pkg/search_mode.py — SearchMode
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class SearchMode(Enum):
    """Search modes with different depth/breadth tradeoffs."""
    QUICK = "quick"         # Single engine, no crawl
    STANDARD = "standard"   # Multi-engine, shallow crawl
    DEEP = "deep"           # Multi-engine, deep crawl
    ACADEMIC = "academic"   # Academic sources only
    CODE = "code"           # Code repositories only
    NEWS = "news"           # News sources only
    EXHAUSTIVE = "exhaustive"  # All engines, max depth


# ═══════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════



