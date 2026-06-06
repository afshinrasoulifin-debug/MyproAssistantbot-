"""
Minimal Claude Ultra Proxy Server
Accepts Anthropic Messages API format on port 8082
Routes to free AI providers via g4f
"""
import asyncio
import json
import logging
import os
import re
import sys
from aiohttp import web

import g4f

logger = logging.getLogger("claude_ultra_proxy")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

AUTH_TOKEN = os.environ.get("ANTHROPIC_AUTH_TOKEN", "freecc")

# Provider fallback chain
PROVIDER_CHAIN = [
    (g4f.Provider.OperaAria, "aria"),
    (g4f.Provider.Qwen_Qwen_3, "qwen3-235b-a22b"),
    (g4f.Provider.PollinationsAI, "openai"),
]


def strip_thinking(text: str) -> str:
    """Remove Qwen thinking blocks from response."""
    # Pattern: starts with "Okay, the user..." or thinking text, ends with "End of Thought"
    # Strip everything before "End of Thought (XXs)\n"
    match = re.search(r'End of Thought\s*\([^)]*\)\s*\n', text)
    if match:
        text = text[match.end():]
    # Also strip <think>...</think> blocks
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Strip "Okay, the user..." preamble if response starts with thinking
    if text.startswith(("Okay, ", "The user ", "Let me ", "Alright, ")):
        # Find the actual response after thinking
        lines = text.split('\n')
        # Find first line that looks like actual content (not meta-thinking)
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if line_stripped and not any(line_stripped.startswith(p) for p in 
                ["Okay", "The user", "Let me", "Alright", "I should", "Maybe", "Hmm", 
                 "So ", "Wait", "Actually", "I think", "They want", "I need"]):
                text = '\n'.join(lines[i:])
                break
    return text.strip()


async def call_g4f(messages: list[dict], temperature: float = 0.7) -> str:
    """Try providers in fallback chain until one works."""
    last_error = None
    for provider, model in PROVIDER_CHAIN:
        try:
            response = await g4f.ChatCompletion.create_async(
                model=model,
                messages=messages,
                provider=provider,
                timeout=60,
                temperature=temperature,
            )
            if response and len(response.strip()) > 0:
                cleaned = strip_thinking(response)
                if cleaned:
                    logger.info("✅ Provider %s succeeded (%d chars)", provider.__name__, len(cleaned))
                    return cleaned
        except Exception as e:
            logger.warning("❌ Provider %s failed: %s", provider.__name__, str(e)[:100])
            last_error = e
            continue

    raise Exception(f"All providers failed. Last error: {last_error}")


async def handle_messages(request: web.Request) -> web.Response:
    """Handle POST /v1/messages — Anthropic Messages API format."""
    api_key = request.headers.get("x-api-key", "")
    if AUTH_TOKEN and api_key != AUTH_TOKEN:
        return web.json_response(
            {"error": {"type": "auth_error", "message": "Invalid API key"}},
            status=401,
        )

    try:
        body = await request.json()
    except Exception:
        return web.json_response(
            {"error": {"type": "invalid_request", "message": "Invalid JSON"}},
            status=400,
        )

    model_id = body.get("model", "")
    messages = body.get("messages", [])
    system_text = body.get("system", "")
    temperature = body.get("temperature", 0.7)

    logger.info("🟣 Request: model=%s, %d msgs", model_id, len(messages))

    # Build g4f messages
    g4f_msgs = []
    if system_text:
        g4f_msgs.append({"role": "system", "content": system_text})
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            content = "\n".join(text_parts)
        g4f_msgs.append({"role": role, "content": content})

    try:
        result = await call_g4f(g4f_msgs, temperature)
    except Exception as e:
        logger.error("All providers failed: %s", e)
        return web.json_response(
            {"error": {"type": "server_error", "message": str(e)}},
            status=502,
        )

    anthropic_response = {
        "id": "msg_proxy_" + os.urandom(8).hex(),
        "type": "message",
        "role": "assistant",
        "model": model_id,
        "content": [{"type": "text", "text": result}],
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": sum(len(m.get("content", "")) for m in g4f_msgs) // 4,
            "output_tokens": len(result) // 4,
        },
    }

    logger.info("✅ Response: %d chars", len(result))
    return web.json_response(anthropic_response)


async def handle_models(request: web.Request) -> web.Response:
    models = [
        {"id": "claude-sonnet-4-20250514", "display_name": "Claude Sonnet 4"},
        {"id": "claude-opus-4-20250522", "display_name": "Claude Opus 4"},
        {"id": "claude-haiku-4-20250514", "display_name": "Claude Haiku 4"},
        {"id": "claude-3-5-sonnet-20241022", "display_name": "Claude 3.5 Sonnet"},
        {"id": "claude-3-5-haiku-20241022", "display_name": "Claude 3.5 Haiku"},
        {"id": "claude-3-opus-20240229", "display_name": "Claude 3 Opus"},
    ]
    return web.json_response({"data": models})


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/v1/messages", handle_messages)
    app.router.add_get("/v1/models", handle_models)
    app.router.add_get("/health", handle_health)
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8082))
    logger.info("🟣 Claude Ultra Proxy starting on port %d", port)
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=port, print=logger.info)
