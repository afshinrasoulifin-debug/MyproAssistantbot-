

import asyncio
import sys

# Mocking modules to avoid project dependency hell during test
class MockNLP:
    @staticmethod
    def tokenize(text): return text.split()

mock_obj = type('obj', (object,), {'PersianNLP': MockNLP})
sys.modules['handlers.victor.nlp'] = mock_obj

from handlers.victor.victor_agent import VictorAgent

async def main():
    print("🕶️ ACTIVATING TRUE GHOST PROTOCOL...")
    print("🧪 Running Real Stealth & Forensic Wipe Test...")
    agent = VictorAgent()
    result = await agent.run("اجرای تست نفوذ مخفی واقعی و پاکسازی", 1)
    print("\n" + "░"*60)
    print(result)
    print("░"*60)

if __name__ == "__main__":
    asyncio.run(main())


