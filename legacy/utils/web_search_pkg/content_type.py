
"""
web_search_pkg/content_type.py — ContentType
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ContentType(Enum):
    """Types of search result content."""
    WEBPAGE = "webpage"
    PDF = "pdf"
    CODE = "code"
    ACADEMIC = "academic"
    NEWS = "news"
    FORUM = "forum"
    SOCIAL = "social"
    IMAGE = "image"
    VIDEO = "video"




