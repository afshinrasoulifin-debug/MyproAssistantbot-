

import asyncio
import sys

# Mocking modules to avoid project dependency hell
class MockNLP:
    @staticmethod
    def tokenize(text): return text.split()

mock_obj = type('obj', (object,), {'PersianNLP': MockNLP})
sys.modules['handlers.victor.nlp'] = mock_obj

from handlers.victor.victor_agent import VictorAgent
from handlers.victor.victor_tools import VictorTools

async def run_live_test():
    print("🔬 STARTING LIVE SINGULARITY INTEGRATION TEST")
    agent = VictorAgent()
    tools = VictorTools()
    
    # Test 1: Real C Compilation
    print("\n[Test 1] Real C Compilation & Execution...")
    c_code = '#include <stdio.h>\nint main() { printf("Hello from Compiled C Tool!\\n"); return 0; }'
    comp_res = await tools.compile_tool(c_code, "fast_tool")
    print(f"Compilation Result: {comp_res}")
    
    if "successfully" in comp_res:
        exec_res = await tools.execute_binary("fast_tool", [])
        print(f"Binary Execution Output: {exec_res.strip()}")
    
    # Test 2: Recursive Reasoning & Unified Execution
    print("\n[Test 2] Recursive Reasoning Chain...")
    task = "تحلیل امنیت فایل‌های سیستم و بهینه‌سازی دسترسی‌ها"
    result = await agent.run(task, 1)
    print(f"Agent Unified Output:\n{result}")
    
    # Test 3: System Resource Interaction
    print("\n[Test 3] Real System Resource Check...")
    cpu = await tools.system_resources()
    print(f"Current CPU Usage: {cpu}%")

if __name__ == "__main__":
    asyncio.run(run_live_test())


