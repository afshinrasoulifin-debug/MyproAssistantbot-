
"""
memory_store_pkg/user_profile.py — UserProfile
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class UserProfile:
    """Tracks user behavior, preferences, and communication style."""
    user_id: str
    display_name: str = ""
    language: str = ""
    preferences: Dict[str, Any] = field(default_factory=dict)
    topics: List[Dict[str, Any]] = field(default_factory=list)
    style: Dict[str, float] = field(default_factory=lambda: {
        "formality": 0.5,
        "verbosity": 0.5,
        "technicality": 0.5,
        "emotionality": 0.5,
        "avg_message_length": 50.0,
    })
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    total_interactions: int = 0
    memory_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "language": self.language,
            "preferences": self.preferences,
            "topics": self.topics,
            "style": self.style,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "total_interactions": self.total_interactions,
            "memory_ids": self.memory_ids,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UserProfile":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})




