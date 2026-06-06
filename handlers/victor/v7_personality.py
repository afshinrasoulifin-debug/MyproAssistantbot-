
from __future__ import annotations
"""Victor v7.0 TITAN — Personality Engine (character development)"""

import time
from collections import defaultdict
from typing import Any, Dict, List


# ═══════════════════════════════════════════════════════════════════
# 7. PERSONALITY ENGINE — v7 Character Development
# ═══════════════════════════════════════════════════════════════════

class PersonalityEngine:
    """
    v7: Victor develops personality traits based on interactions.
    Adjusts response tone, adds character to conversations.
    """

    # Personality dimensions (Big Five inspired, adapted for a bot)
    DIMENSIONS = {
        "playfulness": 0.5,    # Serious ↔ Playful
        "verbosity": 0.5,      # Concise ↔ Verbose
        "formality": 0.5,      # Casual ↔ Formal
        "curiosity": 0.7,      # Passive ↔ Curious
        "confidence": 0.5,     # Humble ↔ Confident
        "warmth": 0.7,         # Cold ↔ Warm
        "humor": 0.3,          # Serious ↔ Humorous
    }

    def __init__(self) -> None:
        self.traits: Dict[str, float] = dict(self.DIMENSIONS)
        self.mood: float = 0.7  # 0.0 = very negative, 1.0 = very positive
        self._mood_history: List[float] = []
        self._interaction_emotions: List[Dict[str, float]] = []
        self.emotional_memories: List[Dict[str, Any]] = []  # memorable emotional moments

    def update_mood(self, sentiment_score: float) -> None:
        """Update mood based on recent interaction sentiment."""
        # Mood is a weighted average: 70% previous, 30% new interaction
        self.mood = max(0.0, min(1.0, self.mood * 0.7 + (sentiment_score + 1.0) / 2.0 * 0.3))
        self._mood_history.append(self.mood)
        if len(self._mood_history) > 100:
            self._mood_history = self._mood_history[-100:]

    def record_emotion(self, emotions: Dict[str, float], text: str = "") -> Any:
        """Record emotional context for personality development."""
        self._interaction_emotions.append(emotions)
        if len(self._interaction_emotions) > 200:
            self._interaction_emotions = self._interaction_emotions[-200:]

        # Save memorable emotional moments (high intensity)
        intensity = sum(emotions.values())
        if intensity > 0.5:
            self.emotional_memories.append({
                "ts": time.time(),
                "emotions": emotions,
                "text_preview": text[:100],
                "mood_at_time": self.mood,
            })
            if len(self.emotional_memories) > 50:
                self.emotional_memories = self.emotional_memories[-50:]

    def evolve_traits(self) -> Any:
        """Evolve personality traits based on accumulated interactions."""
        if len(self._interaction_emotions) < 10:
            return

        recent = self._interaction_emotions[-20:]
        avg_emotions = defaultdict(float)
        for emo_dict in recent:
            for k, v in emo_dict.items():
                avg_emotions[k] += v
        for k in avg_emotions:
            avg_emotions[k] /= len(recent)

        # Adjust traits based on emotional patterns
        if avg_emotions.get("joy", 0) > 0.3:
            self.traits["playfulness"] = min(1.0, self.traits["playfulness"] + 0.02)
            self.traits["humor"] = min(1.0, self.traits["humor"] + 0.01)
        if avg_emotions.get("curiosity", 0) > 0.3:
            self.traits["curiosity"] = min(1.0, self.traits["curiosity"] + 0.02)
        if avg_emotions.get("trust", 0) > 0.3:
            self.traits["warmth"] = min(1.0, self.traits["warmth"] + 0.02)
            self.traits["confidence"] = min(1.0, self.traits["confidence"] + 0.01)
        if avg_emotions.get("anger", 0) > 0.2:
            self.traits["formality"] = min(1.0, self.traits["formality"] + 0.02)
            self.traits["playfulness"] = max(0.0, self.traits["playfulness"] - 0.01)

    def get_tone_modifiers(self) -> Dict[str, str]:
        """Get response tone modifiers based on current personality + mood."""
        modifiers = {}

        if self.mood > 0.7:
            modifiers["greeting_suffix"] = " 😊"
            modifiers["emoji_frequency"] = "high"
        elif self.mood < 0.3:
            modifiers["greeting_suffix"] = ""
            modifiers["emoji_frequency"] = "low"
        else:
            modifiers["greeting_suffix"] = ""
            modifiers["emoji_frequency"] = "medium"

        if self.traits["playfulness"] > 0.7:
            modifiers["style"] = "playful"
        elif self.traits["formality"] > 0.7:
            modifiers["style"] = "formal"
        else:
            modifiers["style"] = "balanced"

        modifiers["verbosity"] = "verbose" if self.traits["verbosity"] > 0.7 else "concise"
        return modifiers

    def get_mood_emoji(self) -> str:
        """Get emoji representing current mood."""
        if self.mood > 0.8:
            return "😄"
        elif self.mood > 0.6:
            return "😊"
        elif self.mood > 0.4:
            return "😐"
        elif self.mood > 0.2:
            return "😔"
        return "😢"

    def format_status(self) -> str:
        """Get personality status report."""
        lines = ["🎭 *شخصیت Victor:*\n"]

        trait_names_fa = {
            "playfulness": "شوخ‌طبعی", "verbosity": "حرف‌زنی",
            "formality": "رسمی‌بودن", "curiosity": "کنجکاوی",
            "confidence": "اعتمادبه‌نفس", "warmth": "صمیمیت",
            "humor": "طنز",
        }

        for trait, value in self.traits.items():
            bar_len = int(value * 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            fa_name = trait_names_fa.get(trait, trait)
            lines.append(f"  {fa_name}: [{bar}] {value:.1%}")

        lines.append(f"\n🌡️ حال و حوصله: {self.get_mood_emoji()} ({self.mood:.0%})")
        lines.append(f"💭 خاطرات احساسی: {len(self.emotional_memories)}")

        return "\n".join(lines)

    def to_dict(self) -> Dict:
        return {
            "traits": self.traits, "mood": self.mood,
            "mood_history": self._mood_history[-50:],
            "emotional_memories": self.emotional_memories[-30:],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PersonalityEngine":
        pe = cls()
        pe.traits.update(data.get("traits", {}))
        pe.mood = data.get("mood", 0.7)
        pe._mood_history = data.get("mood_history", [])
        pe.emotional_memories = data.get("emotional_memories", [])
        return pe


