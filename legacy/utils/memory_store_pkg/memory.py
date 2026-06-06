
"""
memory_store_pkg/memory.py — Memory
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class Memory:
    """A single memory entry."""
    id: str
    type: MemoryType
    content: str
    summary: str = ""
    metadata: MemoryMetadata = field(default_factory=MemoryMetadata)
    embedding: List[float] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    importance: float = 0.5
    tags: List[str] = field(default_factory=list)
    user_id: str = ""
    conversation_id: str = ""

    def age_hours(self) -> float:
        return (time.time() - self.created_at) / 3600

    def staleness_hours(self) -> float:
        return (time.time() - self.last_accessed_at) / 3600

    def retention_score(self, forgetting_rate: float = DEFAULT_FORGETTING_RATE) -> float:
        """
        Ebbinghaus-inspired retention score.
        Higher importance + more access = longer retention.
        """
        freq_boost = 1 + math.log(self.access_count + 1)
        decay = math.exp(-self.staleness_hours() * forgetting_rate)
        return self.importance * freq_boost * decay

    def to_dict(self) -> dict:
        return {
            "id": self.id, "type": self.type.value,
            "content": self.content, "summary": self.summary,
            "metadata": self.metadata.to_dict(),
            "embedding": self.embedding,
            "created_at": self.created_at,
            "last_accessed_at": self.last_accessed_at,
            "access_count": self.access_count,
            "importance": self.importance,
            "tags": self.tags, "user_id": self.user_id,
            "conversation_id": self.conversation_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Memory":
        return cls(
            id=d["id"], type=MemoryType(d["type"]),
            content=d["content"], summary=d.get("summary", ""),
            metadata=MemoryMetadata.from_dict(d.get("metadata", {})),
            embedding=d.get("embedding", []),
            created_at=d.get("created_at", time.time()),
            last_accessed_at=d.get("last_accessed_at", time.time()),
            access_count=d.get("access_count", 0),
            importance=d.get("importance", 0.5),
            tags=d.get("tags", []), user_id=d.get("user_id", ""),
            conversation_id=d.get("conversation_id", ""),
        )




