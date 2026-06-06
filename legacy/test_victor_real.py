

import unittest
import sys
import os

# Ensure we can import the handlers
sys.path.append(os.getcwd())

# Mocking NLP to avoid external dependency for logic testing
class MockNLP:
    @staticmethod
    def tokenize(text): return text.split()

mock_obj = type('obj', (object,), {'PersianNLP': MockNLP})
sys.modules['handlers.victor.nlp'] = mock_obj

from handlers.victor.victor_tools import VictorTools
from handlers.victor.victor_agent import VictorAgent

class TestVictorReal(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tools = VictorTools()
        self.agent = VictorAgent()

    async def test_system_resources(self):
        print("Testing Real System Resources...")
        res = await self.tools.system_resources()
        self.assertIn("cpu_percent", res)
        self.assertIn("memory_usage", res)
        print(f"✅ CPU: {res['cpu_percent']}%")

    async def test_network_scan_local(self):
        print("Testing Real Network Scan (Localhost)...")
        # Scan only a few ports for speed
        res = await self.tools.network_scan("127.0.0.1", range(20, 100))
        self.assertIsInstance(res, list)
        print(f"✅ Found Ports: {res}")

    async def test_file_search(self):
        print("Testing Real File Search...")
        res = await self.tools.file_search("victor_agent.py")
        self.assertTrue(any("victor_agent.py" in f for f in res))
        print(f"✅ Found: {res[0] if res else 'None'}")

    async def test_agent_run(self):
        print("Testing Real Agent Reasoning...")
        res = await self.agent.run("وضعیت سیستم را چک کن و فایل‌های پایتون را پیدا کن", 1)
        self.assertIsInstance(res, str)
        print(f"✅ Agent Response: {res[:100]}...")

if __name__ == "__main__":
    unittest.main()


