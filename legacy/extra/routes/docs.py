
from __future__ import annotations
"""APEX Documentation Routes."""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class DocsRouter:
    """Serve APEX documentation and model info."""

    def __init__(self) -> None:
        self._docs: Dict[str, Dict] = {}
        self._categories = ["models", "tools", "agents", "api"]

    def register_doc(self, category: str, name: str, content: Dict) -> None:
        """Register a documentation entry."""
        key = f"{category}/{name}"
        self._docs[key] = {
            "category": category,
            "name": name,
            **content,
        }

    def get_doc(self, category: str, name: str) -> Dict:
        key = f"{category}/{name}"
        return self._docs.get(key, {"error": "Not found"})

    def list_docs(self, category: str = "") -> List[Dict]:
        if category:
            return [d for d in self._docs.values() if d["category"] == category]
        return list(self._docs.values())

    def get_categories(self) -> List[str]:
        return list(self._categories)

    def search(self, query: str) -> List[Dict]:
        """Search docs by name."""
        q = query.lower()
        return [d for d in self._docs.values() if q in d.get("name", "").lower()]

    def get_stats(self) -> Dict:
        by_cat = {}
        for d in self._docs.values():
            cat = d["category"]
            by_cat[cat] = by_cat.get(cat, 0) + 1
        return {"total": len(self._docs), "by_category": by_cat}


