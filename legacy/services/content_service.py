
from __future__ import annotations
"""
tg_bot/services/content_service.py — Content Business Logic
Extracted from handlers/content_studio.py + content_brain.py

Contains:
  • Content generation strategies
  • Template management
  • Content calendar operations
  • A/B testing for content
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

# ── TITANIUM v29.0 Integration ──


# ── Infrastructure access ──
try:
    from arki_project.services.infra_bridge import get_service_bridge 
except ImportError:
    _get_svc_infra = lambda: None


logger = logging.getLogger(__name__)


@dataclass
class ContentPiece:
    """Structured content data."""
    id: str = ""
    title: str = ""
    body: str = ""
    content_type: str = "post"  # post, story, reel, article, caption
    platform: str = "telegram"
    hashtags: List[str] = field(default_factory=list)
    media_urls: List[str] = field(default_factory=list)
    scheduled_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentTemplate:
    """Reusable content template."""
    id: str = ""
    name: str = ""
    template: str = ""
    variables: List[str] = field(default_factory=list)
    content_type: str = "post"
    language: str = "fa"


class ContentService:
    """Business logic for content operations."""

    def __init__(self):
        self._templates: Dict[str, ContentTemplate] = {}
        self._calendar: List[ContentPiece] = []

    def add_template(self, template: ContentTemplate) -> str:
        """Add a content template."""
        import hashlib, time
        template.id = hashlib.md5(f"{template.name}{time.time()}".encode()).hexdigest()[:10]
        self._templates[template.id] = template
        return template.id

    def get_template(self, template_id: str) -> Optional[ContentTemplate]:
        return self._templates.get(template_id)

    def list_templates(self) -> List[ContentTemplate]:
        return list(self._templates.values())

    def render_template(self, template_id: str, variables: Dict[str, str]) -> str:
        """Render a template with variables."""
        template = self._templates.get(template_id)
        if not template:
            return ""
        result = template.template
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", value)
        return result

    def schedule_content(self, content: ContentPiece) -> str:
        """Schedule content for future publishing."""
        import hashlib, time
        content.id = hashlib.md5(f"{content.title}{time.time()}".encode()).hexdigest()[:10]
        self._calendar.append(content)
        return content.id

    def get_calendar(self, days: int = 7) -> List[ContentPiece]:
        """Get scheduled content for next N days."""
        now = datetime.now()
        return [
            c for c in self._calendar
            if c.scheduled_at and (c.scheduled_at - now).days <= days
        ]

    def generate_hashtags(self, text: str, count: int = 10) -> List[str]:
        """Generate relevant hashtags from text."""
        import re
        words = re.findall(r'\b[\w\u0600-\u06FF]{3,}\b', text)
        # Simple frequency-based selection
        freq = {}
        for w in words:
            w = w.lower()
            freq[w] = freq.get(w, 0) + 1
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [f"#{w}" for w, _ in sorted_words[:count]]


_service: Optional[ContentService] = None

def get_content_service() -> ContentService:
    global _service
    if _service is None:
        _service = ContentService()
    return _service


