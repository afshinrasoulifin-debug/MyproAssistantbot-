
"""
memory_store_pkg/auto_tagger.py — AutoTagger
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class AutoTagger:
    """Auto-generate tags for memories based on content."""

    # Common stop words
    _STOP = {
        "the", "and", "for", "are", "but", "not", "you", "all",
        "can", "had", "her", "was", "one", "our", "out", "has",
        "have", "been", "will", "with", "this", "that", "from",
        "they", "what", "about", "which", "when", "make", "like",
        "time", "just", "know", "take", "come", "more", "some",
        "than", "them", "very", "into", "over", "such", "also",
    }

    @classmethod
    def generate_tags(cls, content: str, max_tags: int = 5) -> list[str]:
        """Extract key terms from content as tags."""
        import re
        from collections import Counter
        words = re.findall(r'\b\w{4,}\b', content.lower())
        filtered = [w for w in words if w not in cls._STOP and not w.isdigit()]
        common = Counter(filtered).most_common(max_tags)
        return [w for w, _ in common]




