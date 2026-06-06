
"""
DDG AI Chat Client — calls the local DDG HTTP server.
No playwright dependency, works with any Python.
"""
import json
import logging
from urllib.request import urlopen, Request
from urllib.error import URLError

logger = logging.getLogger(__name__)
DDG_SERVER = "http://127.0.0.1:9876"


def ddg_chat_sync(messages: list, model: str = "gpt-4o-mini", timeout: int = 45) -> str:
    """Synchronous call to DDG server"""
    req = Request(
        f"{DDG_SERVER}/chat",
        data=json.dumps({"messages": messages, "model": model}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data.get("text", "")
    except Exception as e:
        logger.error("DDG server error: %s", e)
        raise


async def ddg_chat_async(messages: list, model: str = "gpt-4o-mini", timeout: int = 45) -> str:
    """Async call to DDG server (runs sync in executor)"""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: ddg_chat_sync(messages, model, timeout))


def is_ddg_available() -> bool:
    """Check if DDG server is running"""
    try:
        with urlopen(f"{DDG_SERVER}/health", timeout=2) as resp:
            return resp.status == 200
    except:
        return False


