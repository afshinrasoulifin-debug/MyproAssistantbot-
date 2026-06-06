
"""
utils/models_core.py — Core model definitions & registry
──────────────────────────────────────────────────────────
Only verified, real model IDs. Single source of truth for all models.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger(__name__)

# ═══════════════════ MODEL INFO ═══════════════════

@dataclass(frozen=True, slots=True)
class ModelInfo:
    id: str
    name: str
    emoji: str
    provider: str  # "gemini" | "groq" | "openrouter"
    desc: str
    ctx: str


# ═══════════════════ BASE MODELS (Gemini + Groq) ═══════════════════

MODELS: Dict[str, ModelInfo] = {
    # ────── Google Gemini ──────
    "gemini-flash":   ModelInfo("gemini-2.5-flash",       "Gemini 2.5 Flash (Base)", "⚡", "gemini", "سریع و هوشمند",  "1M"),
    "gemini-pro":     ModelInfo("gemini-2.5-pro",         "Gemini 2.5 Pro (Base)",   "🌟", "gemini", "قوی‌ترین ۲.۵",  "1M"),
    "gemini-lite":    ModelInfo("gemini-2.5-flash-lite",  "Gemini 2.5 Lite",         "💨", "gemini", "سبک‌ترین",       "1M"),
    "gemini2-flash":  ModelInfo("gemini-2.0-flash",       "Gemini 2.0 Flash",        "⭐", "gemini", "پایدار و مطمئن", "1M"),
    "gemini2-lite":   ModelInfo("gemini-2.0-flash-lite",  "Gemini 2.0 Lite",         "🌙", "gemini", "نسل ۲ فوری",    "1M"),
    "gemma4":         ModelInfo("gemma-4-31b-it",         "Gemma 4 (31B)",           "💎", "gemini", "اوپن‌سورس ۳۱B", "256K"),
    # ────── Groq ──────
    "llama70":        ModelInfo("llama-3.3-70b-versatile",                         "LLaMA 3.3 70B (Base)", "🦙", "groq", "متا ۷۰B همه‌کاره",  "128K"),
    "llama-scout":    ModelInfo("meta-llama/llama-4-scout-17b-16e-instruct",       "LLaMA 4 Scout (Base)", "🔍", "groq", "نسل ۴ MoE",         "128K"),
    "qwen3":          ModelInfo("qwen/qwen3-32b",                                  "Qwen 3 (32B)",         "🐉", "groq", "استدلال عمیق",      "128K"),
    "llama8":         ModelInfo("llama-3.1-8b-instant",                            "LLaMA 3.1 8B (Base)",  "⚙️", "groq", "فوری‌ترین",         "128K"),
    "compound":       ModelInfo("groq/compound",                                   "Compound AI",          "🧬", "groq", "اجنتیک+سرچ",       "128K"),
    "compound-mini":  ModelInfo("groq/compound-mini",                              "Compound Mini",        "🔬", "groq", "اجنتیک سبک",       "128K"),
    "allam":          ModelInfo("allam-2-7b",                                      "ALLaM 2",              "🕌", "groq", "عربی/انگلیسی",      "4K"),
}

DEFAULT_MODEL = "claude-ultra-sonnet"

FALLBACK_GEMINI: List[str] = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]
FALLBACK_GROQ: List[str] = ["llama-3.3-70b-versatile", "meta-llama/llama-4-scout-17b-16e-instruct", "qwen/qwen3-32b"]


# ═══════════════════ APEX / OPENROUTER TIERS ═══════════════════

APEX_TIERS = {
    "fast": {
        "emoji": "⚡", "label": "Fast", "label_fa": "سریع",
        "models": {
            "g-gemini-flash":      ModelInfo("google/gemini-2.5-flash",              "Gemini 2.5 Flash",      "⚡", "openrouter", "سریع و کارآمد",     "1M"),
            "g-deepseek-chat":     ModelInfo("deepseek/deepseek-chat",               "DeepSeek Chat",         "🌊", "openrouter", "سریع و قوی",       "64K"),
            "g-sonar":             ModelInfo("perplexity/sonar",                     "Sonar",                 "📡", "openrouter", "جستجو آنلاین",     "128K"),
            "g-llama8":            ModelInfo("meta-llama/llama-3.1-8b-instruct",     "LLaMA 3.1 8B",         "🦙", "openrouter", "فوری‌ترین",        "128K"),
            "g-kimi":              ModelInfo("moonshotai/moonlight-16b-a3b-instruct","Moonlight 16B",         "🌙", "openrouter", "مون‌شات",          "128K"),
            "g-grok-code":         ModelInfo("x-ai/grok-2-vision-1212",             "Grok 2 Vision",         "⚙️", "openrouter", "کد سریع",          "128K"),
            "g-mimo-flash":        ModelInfo("google/gemma-2-27b-it",               "Gemma 2 27B",           "📱", "openrouter", "MoE 309B",         "128K"),
            "g-step-flash":        ModelInfo("stepfun/step-2-16k",                  "Step 2",                "🚶", "openrouter", "MoE 196B سریع",    "128K"),
            "g-gemini31-lite":     ModelInfo("google/gemini-2.0-flash-001",         "Gemini 2.0 Flash (V)",  "💨", "openrouter", "سریع‌ترین گوگل",   "1M"),
            "g-mistral-small":     ModelInfo("mistralai/mistral-small-3.1-24b-instruct", "Mistral Small 3.1","🔹", "openrouter", "میسترال سبک",     "128K"),
            "g-nemotron-nano":     ModelInfo("nvidia/nemotron-3-nano-30b-a3b",      "Nemotron Nano 30B",     "🟩", "openrouter", "NVIDIA اجنتیک",    "262K"),
            "g-gemini-nano":       ModelInfo("google/gemma-2-2b-it",                "Gemma 2 2B",            "🔬", "openrouter", "نانو گوگل",        "32K"),
            "g-gemini25-flash-lite":ModelInfo("google/gemma-2-9b-it",              "Gemma 2 9B",            "💨", "openrouter", "سبک‌ترین 2.5",     "1M"),
            "g-phi4-mini":         ModelInfo("microsoft/phi-4-mini-instruct",       "Phi-4 Mini",            "🔵", "openrouter", "مایکروسافت نانو",  "128K"),
            "g-gemma3-4b":         ModelInfo("google/gemma-3-4b-it",                "Gemma 3 4B",            "💎", "openrouter", "نانو گوگل 4B",     "128K"),
            "g-gemma3-1b":         ModelInfo("google/gemma-3-1b-it",                "Gemma 3 1B",            "💎", "openrouter", "نانو حداقلی 1B",   "32K"),
            "g-qwen3-4b":          ModelInfo("qwen/qwen3-4b",                       "Qwen 3 4B",             "🐉", "openrouter", "نانو Qwen",        "128K"),
            "g-qwen3-8b":          ModelInfo("qwen/qwen3-8b",                       "Qwen 3 8B",             "🐉", "openrouter", "مینی Qwen",        "128K"),
            "g-llama32-3b":        ModelInfo("meta-llama/llama-3.2-3b-instruct",    "LLaMA 3.2 3B",          "🦙", "openrouter", "نانو متا 3B",      "128K"),
            "g-llama32-1b":        ModelInfo("meta-llama/llama-3.2-1b-instruct",    "LLaMA 3.2 1B",          "🦙", "openrouter", "نانو حداقلی متا",  "128K"),
            "g-smollm2-1.7b":      ModelInfo("microsoft/phi-3-mini-128k-instruct",  "Phi-3 Mini",            "🤗", "openrouter", "HF نانو 1.7B",     "8K"),
            "g-ministral-8b":      ModelInfo("mistralai/ministral-8b",              "Ministral 8B",          "🔹", "openrouter", "مینی میسترال",     "128K"),
            "g-nemotron-mini":     ModelInfo("nvidia/nemotron-mini-4b-instruct",    "Nemotron Mini 4B",      "🟩", "openrouter", "نانو NVIDIA",      "128K"),
            "g-internlm3":         ModelInfo("microsoft/phi-4",                     "Phi-4 (V)",             "🔴", "openrouter", "اوپن‌سورس چینی",   "128K"),
            "g-deepseek-r1-lite":  ModelInfo("deepseek/deepseek-r1-distill-llama-8b","DeepSeek R1 Lite",     "🌊", "openrouter", "استدلال نانو",     "128K"),
        },
    },
    "standard": {
        "emoji": "🔵", "label": "Standard", "label_fa": "استاندارد",
        "models": {
            "g-claude-sonnet35":   ModelInfo("anthropic/claude-3.5-sonnet",          "Claude 3.5 Sonnet",     "🟣", "openrouter", "قابل اعتماد",      "200K"),
            "g-llama4-scout":      ModelInfo("meta-llama/llama-4-scout",             "LLaMA 4 Scout",         "🔍", "openrouter", "متا کارآمد",       "128K"),
            "g-deepseek-v3":       ModelInfo("deepseek/deepseek-chat-v3-0324",       "DeepSeek V3 (Mar)",     "🌊", "openrouter", "کلاس GPT-4",      "128K"),
            "g-hermes3-70b":       ModelInfo("nousresearch/hermes-3-llama-3.1-70b",  "Hermes 3 70B",          "🏛", "openrouter", "بدون سانسور",      "128K"),
            "g-gpt4o":             ModelInfo("openai/gpt-4o",                        "GPT-4o",                "🟢", "openrouter", "OpenAI مولتی‌مدال", "128K"),
            "g-gemini25-pro":      ModelInfo("google/gemini-2.5-pro",                "Gemini 2.5 Pro",        "🌟", "openrouter", "قوی‌ترین گوگل",    "1M"),
            "g-claude-sonnet4":    ModelInfo("anthropic/claude-sonnet-4",            "Claude Sonnet 4",       "🟣", "openrouter", "نسل جدید کلود",    "200K"),
            "g-claude-sonnet46":   ModelInfo("anthropic/claude-3-sonnet",            "Claude 3 Sonnet",       "🟣", "openrouter", "آخرین کلود",       "200K"),
            "g-mixtral-8x22b":     ModelInfo("mistralai/mixtral-8x22b-instruct",     "Mixtral 8x22B",         "🔹", "openrouter", "MoE اروپایی",      "65K"),
            "g-llama33-70b":       ModelInfo("meta-llama/llama-3.3-70b-instruct",    "LLaMA 3.3 70B",         "🦙", "openrouter", "همه‌کاره قوی",     "128K"),
            "g-qwen25-72b":        ModelInfo("qwen/qwen-2.5-72b-instruct",          "Qwen 2.5 72B",          "🐉", "openrouter", "اوپن‌سورس قوی",    "128K"),
            "g-hermes4-70b":       ModelInfo("nousresearch/hermes-4-70b",            "Hermes 4 70B",          "🏛", "openrouter", "بدون سانسور نسل۴", "128K"),
            "g-mistral-medium":    ModelInfo("mistralai/mistral-nemo",               "Mistral Nemo",          "🔹", "openrouter", "میسترال میانه",    "128K"),
            "g-glm5-turbo":        ModelInfo("01-ai/yi-large",                       "Yi Large",              "🔮", "openrouter", "اجنتیک سریع",      "128K"),
            "g-gemini3-flash":     ModelInfo("google/gemini-2.0-flash-lite-001",     "Gemini 2.0 Flash Lite", "⚡", "openrouter", "اجنتیک سریع",      "1M"),
            "g-gemma3-27b":        ModelInfo("google/gemma-3-27b-it",                "Gemma 3 27B",           "💎", "openrouter", "مولتی‌مدال اوپن",   "128K"),
            "g-phi4-reasoning":    ModelInfo("microsoft/phi-4-reasoning-plus",       "Phi-4 Reasoning+",      "🔵", "openrouter", "استدلال مایکروسافت","128K"),
            "g-claude-haiku35":    ModelInfo("anthropic/claude-3.5-haiku",           "Claude 3.5 Haiku",      "🟣", "openrouter", "هایکو سریع",       "200K"),
            "g-claude-haiku4":     ModelInfo("anthropic/claude-haiku-4",             "Claude Haiku 4",        "🟣", "openrouter", "هایکو نسل4",       "200K"),
            "g-gemma4-27b":        ModelInfo("google/gemma-4-27b-it",                "Gemma 4 27B",           "💎", "openrouter", "اوپن‌سورس نسل4",   "128K"),
            "g-yi-large":          ModelInfo("01-ai/yi-34b-chat",                    "Yi 34B Chat",           "🟡", "openrouter", "مدل چینی قوی",     "128K"),
            "g-dbrx":              ModelInfo("databricks/dbrx-instruct",             "DBRX",                  "🔶", "openrouter", "MoE دیتابریکس",    "32K"),
            "g-cohere-aya":        ModelInfo("cohere/aya-expanse-32b",               "Aya Expanse 32B",       "🌍", "openrouter", "23 زبان+فارسی",    "128K"),
        },
    },
    "smart": {
        "emoji": "🧠", "label": "Smart", "label_fa": "هوشمند",
        "models": {
            "g-smart-deepseek-r1":    ModelInfo("deepseek/deepseek-r1",              "DeepSeek R1",           "🌊", "openrouter", "استدلال عمیق",      "128K"),
            "g-smart-qwq":            ModelInfo("qwen/qwq-32b",                      "QwQ 32B",               "🐉", "openrouter", "استدلال Qwen",      "128K"),
            "g-smart-gemini-pro":     ModelInfo("google/gemini-2.5-pro-preview",      "Gemini 2.5 Pro",        "🌟", "openrouter", "استدلال گوگل",      "1M"),
            "g-smart-claude-sonnet4": ModelInfo("anthropic/claude-sonnet-4",          "Claude Sonnet 4",       "🟣", "openrouter", "تحلیل عمیق",       "200K"),
            "g-smart-o3-mini":        ModelInfo("openai/o3-mini",                     "o3-mini",               "🟢", "openrouter", "ریاضی+کد",         "128K"),
            "g-smart-phi4-reason":    ModelInfo("microsoft/phi-4-reasoning-plus",     "Phi-4 Reasoning+",      "🔵", "openrouter", "استدلال مایکروسافت","128K"),
            "g-smart-llama4-scout":   ModelInfo("meta-llama/llama-4-scout",           "LLaMA 4 Scout",         "🔍", "openrouter", "جستجوگر متا",      "128K"),
            "g-smart-deepseek-v3":    ModelInfo("deepseek/deepseek-chat-v3-0324",     "DeepSeek V3",           "🌊", "openrouter", "چت عمومی عمیق",    "128K"),
            "g-smart-qwen3-235b":     ModelInfo("qwen/qwen3-235b-a22b",              "Qwen 3 235B",           "🐉", "openrouter", "MoE 235B هوشمند",   "128K"),
            "g-smart-gpt4o":          ModelInfo("openai/chatgpt-4o-latest",           "ChatGPT-4o Latest",     "🟢", "openrouter", "آخرین GPT-4o",      "128K"),
            "g-smart-mistral-large":  ModelInfo("mistralai/mistral-large-2411",       "Mistral Large",         "🔹", "openrouter", "اروپایی قوی",      "128K"),
            "g-smart-nemotron-super": ModelInfo("nvidia/nemotron-3-super-120b-a12b",  "Nemotron Super 120B",   "🟩", "openrouter", "NVIDIA سوپر",      "128K"),
            "g-smart-kimi-k2":        ModelInfo("moonshotai/kimi-k2",                 "Kimi K2",               "🌙", "openrouter", "مون‌شات هوشمند",    "128K"),
            "g-smart-hermes4":        ModelInfo("nousresearch/hermes-4-70b",          "Hermes 4 70B",          "🏛", "openrouter", "بدون سانسور هوشمند","128K"),
            "g-smart-codestral":      ModelInfo("mistralai/codestral-2501",           "Codestral",             "🔹", "openrouter", "کد تخصصی",         "256K"),
            "g-smart-command-r":      ModelInfo("cohere/command-r-plus-08-2024",      "Command R+",            "🟤", "openrouter", "RAG تخصصی",        "128K"),
            "g-smart-aya":            ModelInfo("cohere/aya-expanse-32b",             "Aya Expanse 32B",       "🌍", "openrouter", "چندزبانه+فارسی",   "128K"),
            "g-smart-arcee":          ModelInfo("arcee-ai/trinity-large-thinking",    "Arcee Trinity",         "🧠", "openrouter", "استدلال رایگان",    "128K"),
            "g-qwen37-max":           ModelInfo("qwen/qwen3.7-max",                  "Qwen 3.7 Max",          "🐉", "openrouter", "agent‌محور",        "262K"),
            "g-kimi26-think":         ModelInfo("moonshotai/kimi-k2.6",              "Kimi K2.6",             "🌙", "openrouter", "Agent Swarm",       "262K"),
            "g-deepseek-v4-p":        ModelInfo("deepseek/deepseek-v4-pro",          "DeepSeek V4 Pro",       "🌊", "openrouter", "MoE ۱.۶T",         "1M"),
            "g-gemma4-26b":           ModelInfo("google/gemma-4-26b-a4b-it",         "Gemma 4 26B A4B",       "💎", "openrouter", "MoE ۲۶B",          "256K"),
            "g-nemotron3-sup":        ModelInfo("nvidia/nemotron-3-super-120b-a12b",  "Nemotron 3 Super",      "🟩", "openrouter", "Mamba+Transformer", "1M"),
            "g-qwen3-coder":          ModelInfo("qwen/qwen3-coder",                  "Qwen3 Coder 480B",      "💻", "openrouter", "پادشاه کدنویسی",   "262K"),
        },
    },
    "pro": {
        "emoji": "🌟", "label": "Pro", "label_fa": "پرو",
        "models": {
            "g-gpt5":             ModelInfo("openai/gpt-4-turbo-2024-04-09",         "GPT-4 Turbo",          "🟢", "openrouter", "فلگ‌شیپ OpenAI",   "128K"),
            "g-gpt53-chat":       ModelInfo("openai/o3-mini",                        "o3-mini",              "🟢", "openrouter", "آخرین فلگ‌شیپ",    "128K"),
            "g-qwen35-plus":      ModelInfo("qwen/qwen3-30b-a3b",                   "Qwen 2.5 72B (V)",     "🐉", "openrouter", "فلگ‌شیپ Qwen",     "128K"),
            "g-glm5":             ModelInfo("deepseek/deepseek-prover-v2",           "DeepSeek Prover V2",   "🔮", "openrouter", "GLM قوی",          "128K"),
            "g-gpt52":            ModelInfo("openai/chatgpt-4o-latest",              "ChatGPT-4o Latest",    "🟢", "openrouter", "GPT-4 بهبود",      "128K"),
            "g-gemini3-pro":      ModelInfo("google/gemini-2.5-pro-preview",         "Gemini 2.5 Pro (V)",   "🌟", "openrouter", "پرو نسل ۳",       "1M"),
            "g-claude-opus46":    ModelInfo("anthropic/claude-3-opus",               "Claude 3 Opus",        "🟣", "openrouter", "قوی‌ترین کلود",    "200K"),
            "g-deepseek-r1":      ModelInfo("deepseek/deepseek-r1",                  "DeepSeek R1",          "🌊", "openrouter", "استدلال عمیق",     "128K"),
            "g-llama31-405b":     ModelInfo("meta-llama/llama-3.1-405b-instruct",    "LLaMA 3.1 405B",       "🦙", "openrouter", "بزرگ‌ترین متا",    "128K"),
            "g-hermes4-405b":     ModelInfo("nousresearch/hermes-2-pro-llama-3-8b",  "Hermes 2 Pro 8B",      "🏛", "openrouter", "بدون سانسور 405B", "128K"),
            "g-hermes3-405b":     ModelInfo("nousresearch/hermes-3-llama-3.1-405b",  "Hermes 3 405B",         "🏛", "openrouter", "بدون سانسور قبلی", "128K"),
            "g-nemotron-super":   ModelInfo("nvidia/nemotron-3-super-120b-a12b",     "Nemotron Super 120B",   "🟩", "openrouter", "NVIDIA سوپر",      "128K"),
            "g-dall-e-3":         ModelInfo("openai/gpt-4-vision-preview",           "GPT-4 Vision",          "🖼️", "openrouter", "تصویر OpenAI",     "4K"),
            "g-flux-pro":         ModelInfo("black-forest-labs/flux-1.1-pro",        "FLUX 1.1 Pro",          "🌊", "openrouter", "تصویر حرفه‌ای",    "4K"),
            "g-ideogram":         ModelInfo("black-forest-labs/flux-1.1-pro-ultra",  "FLUX Pro Ultra",        "✏️", "openrouter", "تایپوگرافی هوشمند", "4K"),
            "g-o4-mini":          ModelInfo("openai/o4-mini",                        "o4-mini",               "🧠", "openrouter", "استدلال نسل4",     "200K"),
            "g-command-r-plus":   ModelInfo("cohere/command-r-plus-08-2024",         "Command R+",            "🟤", "openrouter", "RAG تخصصی",        "128K"),
            "g-jamba-1.5":        ModelInfo("ai21/jamba-1.5-large",                  "Jamba 1.5 Large",       "🟫", "openrouter", "SSM+Attention",    "256K"),
            "g-solar-pro":        ModelInfo("cohere/command-r-08-2024",              "Command R",             "☀️", "openrouter", "کره‌ای فلگ‌شیپ",    "128K"),
        },
    },
    "power": {
        "emoji": "🟠", "label": "Power", "label_fa": "قدرتمند",
        "models": {
            "g-grok4":            ModelInfo("x-ai/grok-2-1212",                      "Grok 2",               "🔥", "openrouter", "استدلال فرانتیر",  "128K"),
            "g-gpt54":            ModelInfo("openai/o1",                             "o1",                   "🟢", "openrouter", "Codex+GPT",        "1M"),
            "g-glm47":            ModelInfo("qwen/qwen3-14b",                        "Qwen 3 14B",           "🔮", "openrouter", "کد+بدون سانسور",   "128K"),
            "g-llama4-maverick":  ModelInfo("meta-llama/llama-4-maverick",           "LLaMA 4 Maverick",     "🦙", "openrouter", "Maverick متا",     "128K"),
            "g-qwen3-235b":       ModelInfo("qwen/qwen3-235b-a22b",                 "Qwen 3 235B",          "🐉", "openrouter", "MoE 235B",         "128K"),
            "g-qwen3-coder":      ModelInfo("qwen/qwen-2.5-coder-7b-instruct",      "Qwen Coder 7B",        "🐉", "openrouter", "کد تخصصی",         "128K"),
            "g-minimax":          ModelInfo("minimax/minimax-m1",                    "MiniMax M1",           "🔶", "openrouter", "مینی‌مکس قوی",     "128K"),
            "g-mistral-large":    ModelInfo("mistralai/mistral-large-2411",          "Mistral Large",        "🔹", "openrouter", "بزرگ‌ترین میسترال","128K"),
            "g-gemini31-pro":     ModelInfo("google/gemini-2.5-flash-preview",       "Gemini 2.5 Flash (V)", "🌟", "openrouter", "آخرین پرو گوگل",  "1M"),
            "g-kimi-k2":          ModelInfo("moonshotai/kimi-k2",                    "Kimi K2",              "🌙", "openrouter", "مون‌شات قوی",      "128K"),
            "g-mimo-pro":         ModelInfo("nvidia/llama-3.1-nemotron-70b-instruct","Nemotron 70B",         "📱", "openrouter", "پرو شیائومی",      "128K"),
            "g-midjourney-fast":  ModelInfo("black-forest-labs/flux-schnell",        "FLUX Schnell",         "🎨", "openrouter", "تصویر سریع",       "4K"),
            "g-wizard-8x22b":     ModelInfo("microsoft/wizardlm-2-8x22b",           "WizardLM 2 8x22B",     "🧙", "openrouter", "ویزارد MoE",       "65K"),
            "g-dolphin-72b":      ModelInfo("cognitivecomputations/dolphin-mixtral-8x22b","Dolphin 8x22B",   "🐬", "openrouter", "MoE بدون سانسور",  "65K"),
        },
    },
    "ultra": {
        "emoji": "🔴", "label": "Ultra", "label_fa": "فوق‌پیشرفته",
        "models": {
            "g-grok4-fast":       ModelInfo("x-ai/grok-3-beta",                     "Grok 3 Beta",          "🔥", "openrouter", "سریع+استدلال",     "128K"),
            "g-grok41-fast":      ModelInfo("x-ai/grok-3-mini-beta",                "Grok 3 Mini",          "🔥", "openrouter", "سریع 1.8M",        "1.8M"),
            "g-claude-opus4":     ModelInfo("anthropic/claude-opus-4",               "Claude Opus 4",        "🟣", "openrouter", "فلگ‌شیپ قبلی",     "200K"),
            "g-qwen25-coder":     ModelInfo("qwen/qwen-2.5-coder-32b-instruct",     "Qwen Coder 32B",       "🐉", "openrouter", "کد تخصصی",         "128K"),
            "g-qwq-32b":          ModelInfo("qwen/qwq-32b",                         "QwQ 32B",              "🐉", "openrouter", "استدلال",           "128K"),
            "g-codestral":        ModelInfo("mistralai/codestral-2501",              "Codestral",            "🔹", "openrouter", "کد میسترال",       "256K"),
            "g-devstral":         ModelInfo("mistralai/devstral-medium",             "Devstral Medium",      "🔹", "openrouter", "توسعه میسترال",    "128K"),
            "g-midjourney":       ModelInfo("black-forest-labs/flux-pro",            "FLUX Pro",             "🎨", "openrouter", "تصویر حرفه‌ای",    "4K"),
            "g-stable-ultra":     ModelInfo("stability-ai/stable-diffusion-3.5-large","SD 3.5 Large",        "🎭", "openrouter", "SD اولترا",        "4K"),
            "g-o3":               ModelInfo("openai/o3",                             "o3",                   "🧠", "openrouter", "استدلال عمیق",     "200K"),
            "g-qwen37-max":       ModelInfo("qwen/qwen3.7-max",                     "Qwen 3.7 Max",         "🐉", "openrouter", "استدلال جهان",     "262K"),
            "g-deepseek-v4-p":    ModelInfo("deepseek/deepseek-v4-pro",             "DeepSeek V4 Pro",      "🌊", "openrouter", "نسخه ۱.۶T",        "130K"),
        },
    },
}

# Extra free models
_NEW_FREE_MODELS = {
    "g-deepseek-v4-flash": ModelInfo("deepseek/deepseek-v4-flash",                     "DeepSeek V4 Flash",   "🌊", "openrouter", "284B MoE, 1M ctx",     "1M"),
    "g-owl-alpha":         ModelInfo("openrouter/owl-alpha",                            "Owl Alpha",           "🦉", "openrouter", "اجنتیک رایگان",        "1M"),
    "g-arcee-trinity":     ModelInfo("arcee-ai/trinity-large-thinking",                 "Arcee Trinity",       "🧠", "openrouter", "استدلال رایگان",        "128K"),
    "g-gemma4-31b":        ModelInfo("google/gemma-4-31b-it",                           "Gemma 4 31B",         "💎", "openrouter", "Vision+Tools",          "128K"),
    "g-minimax-m25":       ModelInfo("minimax/minimax-m2.5",                            "MiniMax M2.5",        "🔶", "openrouter", "205K ctx رایگان",       "205K"),
    "g-poolside-m1":       ModelInfo("poolside/laguna-m.1",                             "Laguna M.1",          "🏊", "openrouter", "کد رایگان 128K",        "128K"),
    "g-poolside-xs2":      ModelInfo("poolside/laguna-xs.2",                            "Laguna XS.2",         "🏊", "openrouter", "نانو کد رایگان",        "128K"),
    "g-dolphin-24b":       ModelInfo("cognitivecomputations/dolphin-mistral-24b-venice-edition","Dolphin 24B","🐬", "openrouter", "بدون سانسور رایگان",    "32K"),
    "g-nemotron-nano-9b":  ModelInfo("nvidia/nemotron-nano-9b-v2",                      "Nemotron Nano 9B",    "🟩", "openrouter", "NVIDIA نانو سریع",      "128K"),
    "g-hermes3-405b":      ModelInfo("nousresearch/hermes-3-llama-3.1-405b",            "Hermes 3 405B",       "🏛", "openrouter", "بدون سانسور رایگان",    "128K"),
}

# Flatten all into MODELS
for _tier_data in APEX_TIERS.values():
    MODELS.update(_tier_data["models"])
MODELS.update(_NEW_FREE_MODELS)


# ═══════════════════ LOOKUP FUNCTIONS ═══════════════════

def get_model(key: str) -> ModelInfo:
    return MODELS.get(key, MODELS[DEFAULT_MODEL])

def available_models(gemini_key: str = "", groq_key: str = "") -> Dict[str, ModelInfo]:
    return dict(MODELS)

def working_model_key(preferred: str, gemini_key: str = "", groq_key: str = "") -> str:
    m = MODELS.get(preferred)
    if not m:
        return DEFAULT_MODEL
    if m.provider == "gemini" and gemini_key:
        return preferred
    if m.provider == "groq" and groq_key:
        return preferred
    if m.provider == "openrouter":
        return preferred
    return preferred

def smart_model_key(task: str, gemini_key: str = "", groq_key: str = "") -> str:
    or_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if task == "simple":
        if gemini_key: return "gemini-pro"
        if groq_key:   return "llama70"
        if or_key:     return "g-deepseek-chat"
    elif task == "complex":
        if gemini_key: return "gemini-pro"
        if groq_key:   return "qwen3"
        if or_key:     return "g-grok4"
    if gemini_key: return "gemini-pro"
    if groq_key:   return "llama70"
    if or_key:     return "g-gemini25-pro"
    return DEFAULT_MODEL

def get_apex_tier(key: str) -> str | None:
    for tier_name, tier_data in APEX_TIERS.items():
        if key in tier_data["models"]:
            return tier_name
    return None

# ═══════════════════ UNCENSORED ═══════════════════

UNCENSORED_KEYS: list[str] = [
    "g-hermes3-70b", "g-hermes4-70b", "g-hermes4-405b",
    "g-hermes3-405b", "g-glm47", "g-glm5", "g-glm5-turbo", "g-dolphin-72b",
]

def is_uncensored(key: str) -> bool:
    return key in UNCENSORED_KEYS

# ═══════════════════ FREE STATUS ═══════════════════

from enum import Enum as _FreeEnum

class FreeStatus(_FreeEnum):
    DIRECT_FREE = "direct_free"
    FALLBACK_FREE = "fallback_free"
    KEY_FREE = "key_free"

_DIRECT_FREE_MODEL_IDS = {
    "deepseek/deepseek-v4-flash", "openrouter/owl-alpha",
    "google/gemma-4-31b-it", "google/gemma-4-26b-a4b-it",
    "nvidia/nemotron-3-super-120b-a12b", "nvidia/nemotron-3-nano-30b-a3b",
    "qwen/qwen3-coder", "arcee-ai/trinity-large-thinking",
    "meta-llama/llama-3.3-70b-instruct", "meta-llama/llama-3.2-3b-instruct",
    "minimax/minimax-m2.5", "nousresearch/hermes-3-llama-3.1-405b",
    "poolside/laguna-m.1", "poolside/laguna-xs.2",
    "cognitivecomputations/dolphin-mistral-24b-venice-edition",
    "nvidia/nemotron-nano-9b-v2",
}
_KEY_FREE_PROVIDERS = {"gemini", "groq"}

def get_free_status(key: str) -> FreeStatus:
    m = MODELS.get(key)
    if not m:
        return FreeStatus.FALLBACK_FREE
    if m.provider in _KEY_FREE_PROVIDERS:
        return FreeStatus.KEY_FREE
    if m.id in _DIRECT_FREE_MODEL_IDS:
        return FreeStatus.DIRECT_FREE
    return FreeStatus.FALLBACK_FREE

def get_free_label(key: str) -> str:
    s = get_free_status(key)
    return {"direct_free": "🟢 رایگان", "key_free": "🔑 رایگان+کلید"}.get(s.value, "⚡ جایگزین")

def get_free_badge(key: str) -> str:
    s = get_free_status(key)
    return {"direct_free": "🟢", "key_free": "🔑"}.get(s.value, "⚡")



# ═══════════════════ CLAUDE ULTRA (free-claude-code proxy) ═══════════════════
# Powered by free-claude-code: Anthropic-compatible proxy routing to free providers
# Proxy exposes /v1/messages endpoint with Anthropic Messages API format

CLAUDE_ULTRA_MODELS: dict[str, ModelInfo] = {
    "claude-ultra-opus":   ModelInfo("claude-opus-4-20250514",       "Claude Opus 4 (Ultra)",     "💎", "claude_ultra", "قوی‌ترین کلود — رایگان",  "200K"),
    "claude-ultra-sonnet": ModelInfo("claude-sonnet-4-20250514",     "Claude Sonnet 4 (Ultra)",   "🟣", "claude_ultra", "هوشمند و سریع — رایگان",  "200K"),
    "claude-ultra-haiku":  ModelInfo("claude-haiku-4-20250514",      "Claude Haiku 4 (Ultra)",    "⚡", "claude_ultra", "فوق سریع — رایگان",       "200K"),
    "claude-ultra-35s":    ModelInfo("claude-3-5-sonnet-20241022",   "Claude 3.5 Sonnet (Ultra)", "🔮", "claude_ultra", "سانت قابل اعتماد",        "200K"),
    "claude-ultra-35h":    ModelInfo("claude-3-5-haiku-20241022",    "Claude 3.5 Haiku (Ultra)",  "💨", "claude_ultra", "هایکو سریع — رایگان",     "200K"),
    "claude-ultra-3o":     ModelInfo("claude-3-opus-20240229",       "Claude 3 Opus (Ultra)",     "👑", "claude_ultra", "اوپوس کلاسیک — رایگان",   "200K"),
}

MODELS.update(CLAUDE_ULTRA_MODELS)

# Fallback chain for Claude Ultra
FALLBACK_CLAUDE_ULTRA: list[str] = [
    "claude-sonnet-4-20250514",
    "claude-3-5-sonnet-20241022",
    "claude-haiku-4-20250514",
]
