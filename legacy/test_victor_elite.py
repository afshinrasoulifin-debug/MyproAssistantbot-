

import asyncio
import sys
import os

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from handlers.victor.victor_agent import VictorAgent

async def run_test():
    print("🚀 Starting Elite Victor Test Suite...")
    agent = VictorAgent()
    
    # Test 1: Standard Intelligence
    print("\n[Test 1] Standard Intelligence...")
    res1 = await agent.run("تحلیل پورت‌های باز سیستم", 1)
    print(f"Result: {res1[:100]}...")

    # Test 2: Automation Engine
    print("\n[Test 2] Automation Engine...")
    res2 = await agent.run("فعال‌سازی اتوماسیون برای پایش فضای دیسک", 1)
    print(f"Result: {res2}")

    print("\n✅ All tests completed.")

if __name__ == "__main__":
    asyncio.run(run_test())


