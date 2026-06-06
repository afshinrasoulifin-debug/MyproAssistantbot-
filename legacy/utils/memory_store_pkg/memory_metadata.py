
"""
memory_store_pkg/memory_metadata.py — MemoryMetadata
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class MemoryMetadata:
    """Metadata attached to each memory entry."""
    source: str = ""
    model: str = ""
    confidence: float = 0.0
    topic: str = ""
    language: str = ""
    sentiment: str = ""             # positive | negative | neutral
    word_count: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "source": self.source, "model": self.model,
            "confidence": self.confidence, "topic": self.topic,
            "language": self.language, "sentiment": self.sentiment,
            "word_count": self.word_count,
        }
        d.update(self.extra)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryMetadata":
        known = {"source", "model", "confidence", "topic", "language",
                 "sentiment", "word_count"}
        extra = {k: v for k, v in d.items() if k not in known}
        return cls(
            source=d.get("source", ""),
            model=d.get("model", ""),
            confidence=d.get("confidence", 0.0),
            topic=d.get("topic", ""),
            language=d.get("language", ""),
            sentiment=d.get("sentiment", ""),
            word_count=d.get("word_count", 0),
            extra=extra,
        )




