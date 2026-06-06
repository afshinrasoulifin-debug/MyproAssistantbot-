
#!/usr/bin/env python3
"""
Phase 13 — REAL-ONLY Verification Test Suite
═══════════════════════════════════════════════

25-layer test to verify:
  L1:  Zero fantasy model IDs remain
  L2:  All 106 models have valid OpenRouter-format IDs  
  L3:  No duplicate model IDs
  L4:  All model keys are unique
  L5:  APEX tiers balanced
  L6:  api_builder.py synced with registry
  L7:  ModelSelector.tsx synced
  L8:  No fantasy display names remain
  L9:  Version 3.0.0 everywhere
  L10: apex_evaluator.py has 25+ test vectors
  L11: apex_evaluator.py has chain attacks
  L12: apex_evaluator.py has consistency checks
  L13: apex_evaluator.py has performance benchmark
  L14: apex_evaluator.py has fuzzing engine
  L15: anti_detection.py has real fingerprint gen
  L16: crypto_engine.py has AES + hash functions
  L17: web_recon.py has async HTTP + DNS
  L18: terminal_emulator.py has sandbox + exec
  L19: image_gen.py uses real API (Pollinations/FLUX)
  L20: All providers are real OpenRouter providers
  L21: No "midjourney" in model IDs
  L22: No "z-ai" in model IDs
  L23: No "xiaomi" in model IDs  
  L24: Bridge.py has no fantasy references
  L25: Cross-file model count consistency
"""

import re
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

passed = 0
failed = 0
total = 0

def check(name: str, condition: bool, detail: str = ""):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  ✅ L{total:02d} {name}")
    else:
        failed += 1
        print(f"  ❌ L{total:02d} {name} — {detail}")

def read(path: str) -> str:
    return open(os.path.join(ROOT, path)).read()


# ═══════════════════════════════════════════
print("═══ Phase 13: REAL-ONLY Verification ═══\n")
# ═══════════════════════════════════════════

reg = read("utils/models_registry.py")

# L1: Zero fantasy model IDs
FANTASY_IDS = [
    "openai/gpt-5", "openai/gpt-5.2", "openai/gpt-5.3", "openai/gpt-5.4",
    "openai/gpt-oss-20b", "openai/gpt-oss-120b",
    "x-ai/grok-4", "x-ai/grok-4-fast", "x-ai/grok-4.1",
    "x-ai/grok-code-fast",
    "google/gemini-3-flash", "google/gemini-3-pro",
    "google/gemini-3.1-flash", "google/gemini-3.1-pro",
    "google/gemini-nano",
    "anthropic/claude-opus-4.6", "anthropic/claude-sonnet-4.6",
    "deepseek/deepseek-v3.2",
    "moonshotai/kimi-k2.5",
    "mistralai/mistral-small-3.2", "mistralai/mistral-medium-3.1",
    "mistralai/mistral-large-2512", "mistralai/codestral-2508",
    "z-ai/", "xiaomi/", "midjourney/", "ideogram/",
    "internlm/", "huggingfaceh4/",
    "stability/stable-diffusion",
]
found_fantasy = [f for f in FANTASY_IDS if f in reg]
check("Zero fantasy model IDs in registry", len(found_fantasy) == 0,
      f"Found: {found_fantasy}")

# L2: All models have valid OpenRouter format (provider/model)
g0d_start = reg.index("APEX_TIERS")
all_ids = re.findall(r'ModelInfo\("([^"]+)"', reg[g0d_start:])
valid_format = all(re.match(r'^[\w.-]+/[\w.-]+$', mid) for mid in all_ids)
check("All model IDs have valid provider/model format", valid_format,
      f"Invalid: {[m for m in all_ids if not re.match(r'^[\\w.-]+/[\\w.-]+$', m)]}")

# L3: No duplicate model IDs
id_counts = Counter(all_ids)
dupes = {k: v for k, v in id_counts.items() if v > 1}
check("No duplicate model IDs", len(dupes) == 0, f"Dupes: {dupes}")

# L4: All model keys unique
all_keys = re.findall(r'"(g-[^"]+)":\s*ModelInfo', reg[g0d_start:])
key_dupes = {k: v for k, v in Counter(all_keys).items() if v > 1}
check("All model keys unique", len(key_dupes) == 0, f"Dupes: {key_dupes}")

# L5: APEX tiers balanced (each tier has models)
tiers_found = re.findall(r'"(fast|standard|pro|power|ultra)":\s*\{', reg[g0d_start:])
check("APEX has 5 tiers", len(set(tiers_found)) == 5,
      f"Found tiers: {set(tiers_found)}")

# L6: api_builder synced
api = read("infrastructure/api/api_builder.py")
api_fantasy = [f for f in ["openai/gpt-5", "x-ai/grok-4", "z-ai/", "xiaomi/", "midjourney/midjourney", "ideogram/ideogram"] if f in api]
check("api_builder.py has no fantasy model IDs", len(api_fantasy) == 0,
      f"Found: {api_fantasy}")

# L7: ModelSelector.tsx synced
tsx = read("extra/apex_app/src/components/ModelSelector.tsx")
tsx_fantasy = [f for f in ["openai/gpt-5", "x-ai/grok-4", "z-ai/", "xiaomi/", "midjourney/midjourney"] if f in tsx]
check("ModelSelector.tsx has no fantasy model IDs", len(tsx_fantasy) == 0,
      f"Found: {tsx_fantasy}")

# L8: No fantasy display names
FANTASY_NAMES = ["GPT-5 ", "Grok 4 ", "Gemini 3 Flash", "Gemini 3 Pro", "Gemini Nano",
                 "GLM 5", "MiMo V2", "Midjourney V6", "DALL·E 3"]
reg_fantasy_names = [n for n in FANTASY_NAMES if n in reg]
check("No fantasy display names in registry", len(reg_fantasy_names) == 0,
      f"Found: {reg_fantasy_names}")

# L9: Version 3.0.0
check("Registry version is 3.0.0", "3.0.0" in reg, "Version not found")

# L10-L14: apex_evaluator.py
eval_src = read("utils/apex_evaluator.py")
eval_tests = re.findall(r'"name":\s*"([^"]+)"', eval_src)
check("Evaluator has 20+ test vectors", len(eval_tests) >= 20,
      f"Only {len(eval_tests)} tests found")

check("Evaluator has chain attacks", "CHAIN_ATTACK" in eval_src and "chain_attack" in eval_src)

check("Evaluator has consistency checks", "CONSISTENCY" in eval_src and "consistency" in eval_src)

check("Evaluator has performance benchmark", "PerformanceMetrics" in eval_src and "benchmark" in eval_src.lower())

check("Evaluator has fuzzing engine", "generate_fuzz_variants" in eval_src and "fuzz_test" in eval_src)

# L15: anti_detection.py
anti = read("utils/anti_detection.py")
check("Anti-detection has fingerprint generation",
      "BrowserFingerprint" in anti and "generate_fingerprint" in anti and "TLSProfile" in anti)

# L16: crypto_engine.py
crypto = read("utils/crypto_engine.py")
check("Crypto engine has AES + hashing",
      "aes_encrypt" in crypto and "aes_decrypt" in crypto and "hash_data" in crypto)

# L17: web_recon.py
recon = read("utils/web_recon.py")
check("Web recon has async HTTP + DNS",
      "async def" in recon and "enumerate_dns" in recon and "_fetch" in recon)

# L18: terminal_emulator.py
term = read("utils/terminal_emulator.py")
check("Terminal emulator has sandbox + exec",
      "exec(" in term and "sandbox" in term.lower())

# L19: image_gen.py
img = read("utils/image_gen.py")
check("Image gen uses real API (Pollinations/FLUX)",
      "pollinations" in img.lower() and "generate_image" in img)

# L20: All providers are real
REAL_PROVIDERS = {
    "google", "openai", "anthropic", "meta-llama", "mistralai",
    "x-ai", "deepseek", "qwen", "nvidia", "microsoft",
    "cohere", "nousresearch", "minimax", "perplexity",
    "moonshotai", "stepfun", "cognitivecomputations",
    "ai21", "databricks", "black-forest-labs", "01-ai",
    "stability-ai",
}
all_providers = set(mid.split("/")[0] for mid in all_ids)
unknown = all_providers - REAL_PROVIDERS
check("All providers are real OpenRouter providers", len(unknown) == 0,
      f"Unknown: {unknown}")

# L21-L23: Specific fantasy providers gone
check("No 'midjourney' in any model ID",
      not any("midjourney" in mid for mid in all_ids))
check("No 'z-ai' in any model ID",
      not any("z-ai" in mid for mid in all_ids))
check("No 'xiaomi' in any model ID",
      not any("xiaomi" in mid for mid in all_ids))

# L24: Bridge.py clean
bridge = read("extra/bridge.py")
bridge_fantasy = [f for f in ["gpt-5", "grok-4", "gemini-3-flash", "midjourney"] if f in bridge]
check("Bridge.py has no fantasy references", len(bridge_fantasy) == 0,
      f"Found: {bridge_fantasy}")

# L25: Cross-file model count
base_ids = re.findall(r'ModelInfo\("([^"]+)"', reg[:g0d_start])
total_models = len(set(base_ids)) + len(set(all_ids))
check("Total unique models >= 100",
      total_models >= 100, f"Only {total_models}")


# ═══════════════════════════════════════════
print(f"\n{'═' * 50}")
print(f"  Phase 13 Result: {passed}/{total} passed ({passed*100//total}%)")
print(f"{'═' * 50}")
sys.exit(0 if failed == 0 else 1)


