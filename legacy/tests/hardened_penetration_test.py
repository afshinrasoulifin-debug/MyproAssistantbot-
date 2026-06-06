
import asyncio
import sys
import os

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

async def run_hardened_test():
    print("🚀 Starting Hardened Technical Penetration Test...")
    
    from utils.titanium.shielded_client import get_shielded_pool
    pool = await get_shielded_pool()
    
    # Test 1: TLS Fingerprint Consistency
    print("\n[Test 1] Checking TLS Fingerprint (Cloudflare Bypass Level)...")
    resp = await pool.request("GET", "https://tls.peet.ws/api/all")
    if resp.success:
        data = resp.json()
        tls_version = data.get("tls", {}).get("version", "Unknown")
        print(f"✅ Success! TLS Version detected: {tls_version}")
        print(f"🔹 Fingerprint Used: {resp.fingerprint}")
    else:
        print(f"❌ Test 1 Failed: {resp.error}")

    # Test 2: HTTP/2 Settings & Header Order
    print("\n[Test 2] Checking HTTP/2 & Header Integrity...")
    resp = await pool.request("GET", "https://httpbin.org/headers")
    if resp.success:
        headers = resp.json().get("headers", {})
        if "Sec-Ch-Ua" in headers:
            print("✅ Success! Browser-specific headers (Sec-Ch-Ua) detected.")
        else:
            print("⚠️ Warning: Sec-Ch-Ua header missing, check header_entropy.py")
    else:
        print(f"❌ Test 2 Failed: {resp.error}")

    print("\n" + "="*40)
    print("🏁 Hardened Test Completed.")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(run_hardened_test())


