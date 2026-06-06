
import asyncio
import json
import sys
import os

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

async def test_quantum_penetration():
    print("🔮 Initializing QUANTUM-REAL Penetration Test...")
    
    try:
        from architecture.adapter.transport import QuantumStealthTransport
        transport = QuantumStealthTransport()
    except ImportError as e:
        print(f"❌ Failed to load Quantum Transport: {e}")
        return

    targets = [
        {"name": "TLS Fingerprint", "url": "https://tls.peet.ws/api/all"},
        {"name": "WAF Header Check", "url": "https://httpbin.org/headers"},
        {"name": "HTTP/2 Probe", "url": "https://http2.pro/api/v1"}
    ]

    report = {}

    for target in targets:
        print(f"📡 Probing {target['name']}...")
        try:
            # Test with real quantum transport
            response = await transport.request("GET", target["url"], session_id="quantum_test_unit")
            
            if hasattr(response, "json"):
                data = response.json()
            else:
                data = json.loads(response.text)
                
            report[target["name"]] = {
                "status": "SUCCESS",
                "code": response.status_code,
                "data_preview": str(data)[:100] + "..."
            }
            print(f"✅ {target['name']} Probe Successful.")
        except Exception as e:
            report[target["name"]] = {"status": "FAILED", "error": str(e)}
            print(f"❌ {target['name']} Probe Failed: {e}")

    print("\n" + "="*40)
    print("📊 QUANTUM-REAL FINAL REPORT")
    print("="*40)
    print(json.dumps(report, indent=2))
    
    success_count = sum(1 for r in report.values() if r["status"] == "SUCCESS")
    if success_count == len(targets):
        print("\n🏆 STATUS: QUANTUM-VERIFIED (100% Penetration Efficiency)")
    else:
        print(f"\n⚠️ STATUS: DEGRADED ({success_count}/{len(targets)} Efficiency)")

if __name__ == "__main__":
    asyncio.run(test_quantum_penetration())


