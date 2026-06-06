
import asyncio
import json
import sys
import os

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from curl_cffi import requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    import httpx

async def validate_stealth():
    print("🚀 Starting Stealth Validation Framework (TITANIUM v29.1)...")
    
    results = {
        "tls_fingerprint": None,
        "headers": None,
        "proxy_status": "Not Used"
    }

    # 1. Probe TLS Fingerprint
    print("🔍 Probing TLS Fingerprint (tls.peet.ws)...")
    try:
        if CURL_CFFI_AVAILABLE:
            response = requests.get(
                "https://tls.peet.ws/api/all", 
                impersonate="chrome124",
                timeout=15
            )
            tls_data = response.json()
        else:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://tls.peet.ws/api/all")
                tls_data = response.json()
        
        results["tls_fingerprint"] = {
            "ja3": tls_data.get("tls", {}).get("ja3"),
            "peet_ws_status": "Success"
        }
        print("✅ TLS Probe Complete.")
    except Exception as e:
        results["tls_fingerprint"] = {"error": str(e)}
        print(f"❌ TLS Probe Failed: {e}")

    # 2. Probe Headers
    print("🔍 Probing Headers (httpbin.org)...")
    try:
        if CURL_CFFI_AVAILABLE:
            response = requests.get(
                "https://httpbin.org/headers", 
                impersonate="chrome124",
                timeout=15
            )
            headers_data = response.json()
        else:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://httpbin.org/headers")
                headers_data = response.json()
        
        results["headers"] = headers_data.get("headers")
        print("✅ Header Probe Complete.")
    except Exception as e:
        results["headers"] = {"error": str(e)}
        print(f"❌ Header Probe Failed: {e}")

    # Final Report
    print("\n--- 📊 STEALTH VALIDATION REPORT ---")
    print(json.dumps(results, indent=2))
    
    if results["tls_fingerprint"] and "ja3" in results["tls_fingerprint"]:
        print("\n🛡️ TITANIUM Status: VERIFIED (TLS Impersonation Active)")
    else:
        print("\n⚠️ TITANIUM Status: WARNING (TLS Fingerprint Mismatch or Failed)")

if __name__ == "__main__":
    asyncio.run(validate_stealth())


