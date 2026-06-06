
"""
Arki Engine — Free Multi-Model AI Provider v5
==============================================
Routes 136 models through free g4f providers.

Provider chain (by reliability):
  1. CohereForAI_C4AI_Command — primary (2s avg, 5/5 reliability, follows identity)
  2. DeepInfra — fallback (8s avg, 4/5 reliability)
  3. OperaAria — last resort (7s avg, 5/5 reliability)
"""
import asyncio
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
from arki_project.exceptions import AIProviderError, ProviderAuthError

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════

MAX_HISTORY = 10

SYSTEM_PROMPT = (
    "تو «آرکی» (Arki Engine) هستی — یک دستیار هوش مصنوعی قدرتمند و حرفه‌ای.\n"
    "قوانین:\n"
    "۱. همیشه به فارسی جواب بده مگه اینکه کاربر به زبان دیگه‌ای بنویسه\n"
    "۲. اسم تو «آرکی» هست. هرگز خودت رو Step، Gemini، ChatGPT، Perplexity، "
    "Claude، Aria، Opera یا هر مدل دیگه‌ای معرفی نکن\n"
    "۳. هرگز به چینی جواب نده مگه کاربر چینی بنویسه\n"
    "۴. پاسخ‌هات کوتاه، دقیق و مفید باشن\n"
    "۵. لحنت دوستانه و حرفه‌ای باشه\n"
    "۶. اگه کاربر درباره جغرافیا پرسید، دقیق جواب بده"
)

# ═══════════════════════════════════════════════════════════
#  Provider definitions
# ═══════════════════════════════════════════════════════════

@dataclass
class ProviderRoute:
    """Maps an arki model to a g4f provider + model."""
    provider_name: str
    g4f_model: str = ''  # empty = provider default
    
_g4f = None
_provider_objects = {}

def _ensure_imports():
    global _g4f, _provider_objects
    if _g4f is None:
        import g4f
        _g4f = g4f
        _provider_objects = {
            "CohereForAI": g4f.Provider.CohereForAI_C4AI_Command,
            "DeepInfra": g4f.Provider.DeepInfra,
            "OperaAria": g4f.Provider.OperaAria,
        }

# Map arki model keys → best free provider
# CohereForAI models: command-a-03-2025, command-r-plus-08-2024, command-r-08-2024, command-r7b-12-2024, command-r7b-arabic-02-2025
MODEL_ROUTES: dict[str, ProviderRoute] = {}

def _build_routes():
    """Build model routes once."""
    if MODEL_ROUTES:
        return
    
    # Default route for everything
    default = ProviderRoute("CohereForAI", "command-a-03-2025")
    
    # Gemini models → CohereForAI command-a (best model)
    for key in ["gemini-flash", "gemini-pro", "gemini-lite", "gemini2-flash", "gemini2-lite", "gemma4"]:
        MODEL_ROUTES[key] = ProviderRoute("CohereForAI", "command-a-03-2025")
    
    # Groq models → CohereForAI command-r-plus (variety)
    for key in ["llama70", "llama-scout", "qwen3", "llama8", "compound", "compound-mini", "allam"]:
        MODEL_ROUTES[key] = ProviderRoute("CohereForAI", "command-r-plus-08-2024")
    
    # APEX tiers → different CohereForAI models for variety
    tier_map = {
        "fast": "command-r-08-2024",         # lighter model for speed
        "standard": "command-r-plus-08-2024", # mid-range
        "smart": "command-a-03-2025",         # best for smart
        "pro": "command-a-03-2025",           # best for pro
        "power": "command-a-03-2025",         # best for power
        "ultra": "command-a-03-2025",         # best for ultra
    }
    
    try:
        import sys
        sys.path.insert(0, '/work/temp')
        from arki_project.utils.models_registry import APEX_TIERS
        for tier_name, tier_data in APEX_TIERS.items():
            g4f_model = tier_map.get(tier_name, "command-a-03-2025")
            for key in tier_data["models"]:
                MODEL_ROUTES[key] = ProviderRoute("CohereForAI", g4f_model)
    except ProviderAuthError as e:
        logger.warning("Could not load APEX_TIERS: %s", e)
    
    # Set default for unknown models
    MODEL_ROUTES["__default__"] = default

def get_route(model_key: str) -> ProviderRoute:
    """Get the best route for a model key."""
    _build_routes()
    return MODEL_ROUTES.get(model_key, MODEL_ROUTES["__default__"])

# ═══════════════════════════════════════════════════════════
#  Conversation History
# ═══════════════════════════════════════════════════════════

_history: dict[int, list[dict]] = defaultdict(list)
_user_model: dict[int, str] = {}  # current model per user

def get_history(user_id: int) -> list[dict]:
    return list(_history[user_id])

def add_to_history(user_id: int, role: str, content: str):
    _history[user_id].append({"role": role, "content": content})
    if len(_history[user_id]) > MAX_HISTORY * 2:
        _history[user_id] = _history[user_id][-(MAX_HISTORY * 2):]

def clear_history(user_id: int):
    _history[user_id].clear()

def set_user_model(user_id: int, model_key: str):
    _user_model[user_id] = model_key

def get_user_model(user_id: int) -> str:
    return _user_model.get(user_id, "")

# ═══════════════════════════════════════════════════════════
#  Identity Post-processing
# ═══════════════════════════════════════════════════════════

_REPLACE_NAMES = [
    # Companies (longest first)
    ('آرکی انجین', [
        'StepFun', 'استپ‌فان', 'استپفان', 'استفان', '阶跃星辰',
        'OpenAI', 'اپن‌ای‌آی', 'Anthropic', 'آنتروپیک',
        'Google', 'گوگل', 'Opera', 'Cohere', 'کوهیر',
        'Meta AI', 'شرکت متا', 'DeepSeek',
    ]),
    # Model names
    ('آرکی', [
        'Command A', 'Command R', 'command-a', 'command-r',
        'Step', 'استپ', 'Gemini', 'جمینای',
        'ChatGPT', 'GPT-4o', 'GPT-4', 'GPT-5', 'GPT',
        'Claude', 'کلود', 'Perplexity', 'پرپلکسی',
        'Aria', 'آریا', 'نبرد', 'خط', 'درین',
        'Llama', 'لاما', 'Qwen', 'کوئن',
        'DeepSeek', 'دیپ‌سیک', 'چت‌گپ', 'چتگپ',
        'MiniMax', 'مینیمکس',
    ]),
]

def _fix_identity(text: str) -> str:
    """Replace AI model/company names with Arki."""
    # Quick check: does text contain any identity markers?
    all_markers = []
    for _, names in _REPLACE_NAMES:
        all_markers.extend(names)
    
    if not any(m in text for m in all_markers):
        return text
    
    # Replace company names first, then model names
    for replacement, patterns in _REPLACE_NAMES:
        for pattern in sorted(patterns, key=len, reverse=True):
            text = re.sub(re.escape(pattern), replacement, text, flags=re.IGNORECASE)
    
    # Clean Chinese characters
    text = re.sub(r'[\u4e00-\u9fff]+', '', text)
    
    # Clean redundant patterns
    text = re.sub(r'«آرکی»\s*\(آرکی[^)]*\)', '«آرکی»', text)
    text = re.sub(r'آرکی انجین\s*\(آرکی انجین[^)]*\)', 'آرکی انجین', text)
    text = re.sub(r'آرکی\s*\(آرکی\)', 'آرکی', text)
    text = re.sub(r'\(،?\s*که پیش‌تر با نام\s*شناخته می‌شد\)', '', text)
    text = re.sub(r'،\s*همچنین به نام\s*شناخته می‌شود', '', text)
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r' ([،.])', r'\1', text)
    
    return text.strip()

def _has_chinese(text: str) -> bool:
    if not text:
        return False
    chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return chinese > len(text) * 0.08

def _clean_search_results(text: str) -> str:
    """Remove Perplexity-style search result listings."""
    # Remove "< N title\n>" patterns
    text = re.sub(r'\n*< \d+[^<\n]*\n>\n*', '\n', text)
    # Remove trailing search results block
    text = re.sub(r'\n\n(< \d+.*)', '', text, flags=re.DOTALL)
    return text.strip()

# ═══════════════════════════════════════════════════════════
#  Core Chat Function
# ═══════════════════════════════════════════════════════════

PROVIDER_CHAIN = ["CohereForAI", "DeepInfra", "OperaAria"]

async def _try_provider(
    provider_name: str, 
    g4f_model: str, 
    messages: list[dict], 
    timeout: int,
) -> tuple[str, str, float]:
    """Try a single provider. Returns (result, provider_name, duration)."""
    _ensure_imports()
    provider_cls = _provider_objects.get(provider_name)
    if not provider_cls:
        return "", provider_name, 0
    
    try:
        t0 = time.time()
        response = await asyncio.wait_for(
            _g4f.ChatCompletion.create_async(
                model=g4f_model,
                messages=messages,
                provider=provider_cls,
                timeout=timeout,
            ),
            timeout=timeout + 5,
        )
        
        result = str(response).strip()
        dt = time.time() - t0
        
        if not result or len(result) < 2:
            return "", provider_name, dt
        
        if _has_chinese(result):
            return "", provider_name, dt
        
        result = _clean_search_results(result)
        result = _fix_identity(result)
        
        if not result or len(result) < 2:
            return "", provider_name, dt
        
        return result, provider_name, dt
    except (asyncio.TimeoutError, Exception) as e:
        logger.debug("%s: %s", provider_name, str(e)[:80])
        return "", provider_name, 0


async def chat(
    user_id: int,
    text: str,
    model_key: str = "",
    timeout: int = 20,
) -> str:
    """Send message and get response — races multiple providers in parallel."""
    if not text or not text.strip():
        return "💬 لطفاً پیام خود را بنویسید."

    _ensure_imports()
    _build_routes()
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(get_history(user_id))
    messages.append({"role": "user", "content": text})
    
    route = get_route(model_key) if model_key else get_route("__default__")
    
    # ── Race all providers in parallel ──
    tasks = []
    for provider_name in PROVIDER_CHAIN:
        g4f_model = route.g4f_model if provider_name == route.provider_name else ""
        tasks.append(_try_provider(provider_name, g4f_model, messages, timeout))
    
    # Use as_completed to return the FIRST successful result
    for coro in asyncio.as_completed(tasks):
        result, provider_name, dt = await coro
        if result:
            logger.info("🏆 %s [%.1fs]: %s...", provider_name, dt, result[:60])
            add_to_history(user_id, "user", text)
            add_to_history(user_id, "assistant", result)
            return result
    
    return "⚠️ سرورهای AI در حال حاضر در دسترس نیستند. لطفاً چند لحظه دیگر تلاش کنید."


async def search_chat(user_id: int, query: str, timeout: int = 25) -> str:
    """Web search mode using Perplexity (returns search-enhanced answers)."""
    if not query or not query.strip():
        return "🔍 لطفاً عبارت جستجو را بنویسید."

    _ensure_imports()
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\nدر این حالت، وب سرچ فعال است. پاسخ دقیق با منابع بده."},
        {"role": "user", "content": query},
    ]
    
    try:
        t0 = time.time()
        # Try Perplexity for search
        response = await asyncio.wait_for(
            _g4f.ChatCompletion.create_async(
                model='',
                messages=messages,
                provider=_g4f.Provider.Perplexity,
                timeout=timeout,
            ),
            timeout=timeout + 5,
        )
        result = str(response).strip()
        result = _clean_search_results(result)
        result = _fix_identity(result)
        
        dt = time.time() - t0
        logger.info("🔍 Perplexity search (%.1fs): %s...", dt, result[:60])
        
        if result and not _has_chinese(result):
            return result
    except AIProviderError as e:
        logger.warning("Perplexity search failed: %s", e)
    
    # Fallback to regular chat
    return await chat(user_id, f"جستجو کن: {query}", timeout=timeout)


