

import asyncio
import sys

# Mocking modules to avoid project dependency hell during test
class MockNLP:
    @staticmethod
    def tokenize(text): return text.split()
    def extract_entities(self, text): return []
    def detect_question_type(self, text): return "general"

mock_obj = type('obj', (object,), {
    'PersianNLP': MockNLP,
    'PersianTextToolkit': MockNLP
})
sys.modules['handlers.victor.nlp'] = mock_obj

from handlers.victor.victor_agent import VictorAgent

async def run_isolated_test():
    print("🧪 Running Isolated Victor Logic Test...")
    agent = VictorAgent()
    
    # Test Automation & System Tools
    print("Testing System Audit & Automation...")
    res = await agent.run("تست اتوماسیون سیستم", 1)
    print(f"Result: {res}")
    
    # Test Memory
    print("\nTesting Memory Storage...")
    mid = await agent.teach("تست دانش", "ویکتور اکنون کاملاً فعال است.", 1)
    print(f"Memory ID: {mid}")
    
    print("\n✅ Logic Verification Complete.")

if __name__ == "__main__":
    asyncio.run(run_isolated_test())


