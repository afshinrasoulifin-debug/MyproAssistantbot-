
from __future__ import annotations
import logging
from .victor_agent import VictorAgent
from .victor_memory import VictorMemory
from .nlp import PersianNLP

logger = logging.getLogger(__name__)

class VictorBrain:
    """
    TITAN v29.0 PRO - The Ultimate Brain.
    High-level orchestrator for Victor's autonomous operations.
    """
    def __init__(self) -> None:
        self.agent = VictorAgent()
        self.memory = VictorMemory()
        self.nlp = PersianNLP()
        logger.info("🚀 TITAN v29.0 PRO Brain Activated.")

    async def process(self, text: str, user_id: int = 0) -> str:
        """
        Unified processing pipeline: NLP Analysis -> Strategy Selection -> Execution.
        """
        text = text.strip()
        if not text: return "🤔"

        # 1. NLP Pre-processing
        intent = self.nlp.detect_question_type(text)
        entities = self.nlp.extract_entities(text)
        
        # 2. Strategy Routing
        # Use Agent Loop for research, coding, or multi-step tasks
        is_complex = any(k in text for k in ["تحقیق", "کد", "تحلیل", "بررسی", "گزارش"])
        
        if is_complex or len(text.split()) > 6:
            logger.info(f"TITAN Routing: Complex task detected. User: {user_id}")
            return await self.agent.run(text, user_id)
        
        # 3. Memory Recall for simple queries
        hits = await self.memory.recall(text, top_k=2)
        if hits:
            return f"بر اساس دانش من:\n{hits[0]['content']}"

        return f"من ویکتور هستم، نسخه TITAN v29. برای کارهای پیچیده در خدمتم. شما گفتید: {text}"

    async def teach(self, topic: str, knowledge: str, user_id: int) -> str:
        """Teach Victor new persistent knowledge."""
        mid = await self.memory.store(knowledge, topic, {"user_id": user_id})
        return f"TITAN Memory Updated. Knowledge ID: {mid}"

    def get_status(self) -> str:
        return "TITAN v29.0 PRO is operational."


