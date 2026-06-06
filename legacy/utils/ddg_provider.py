
"""
DuckDuckGo AI Chat Provider v4 — Separate intercept + response capture
- route() modifies outgoing request body (keeps native headers)
- page.on("response") captures the SSE response
"""
import asyncio, json, logging

logger = logging.getLogger(__name__)

_browser = None
_lock = asyncio.Lock()


async def _get_browser():
    """Get or create browser, recreating if closed."""
    global _browser
    from sdk.utils.browser import get_browser, close_browser
    
    if _browser is not None:
        try:
            await _browser.page.evaluate("() => true")
            return _browser
        except Exception:
            logger.info("Browser was closed, recreating...")
            try:
                await close_browser("ddg-prod")
            except: pass
            _browser = None
    
    _browser = await get_browser("ddg-prod", starting_url="about:blank")
    await asyncio.sleep(1)
    return _browser


async def ddg_chat(messages: list, model: str = "gpt-4o-mini") -> str:
    """Send messages to DDG AI Chat. Returns AI response text."""
    async with _lock:
        browser = await _get_browser()
        
        user_msg = ""
        for m in messages:
            if m["role"] == "user":
                user_msg = m["content"]
        if not user_msg:
            return ""
        
        logger.info(f"DDG chat request: {user_msg[:50]}...")
        
        # State for capturing response
        response_chunks = []
        response_done = asyncio.Event()
        intercept_active = False  # Only intercept the POST we trigger
        
        # Clean up old routes
        try:
            await browser.page.unroute("**/duckchat/v1/chat")
        except: pass
        
        # Remove old response listeners
        browser.page.remove_listener("response", lambda r: None)
        
        async def modify_request(route):
            """Only modify POST requests with a body (the actual chat send)."""
            req = route.request
            if req.method == "POST" and req.post_data and intercept_active:
                try:
                    body = json.loads(req.post_data)
                    body["messages"] = messages
                    logger.info("Intercepted POST, injected messages")
                    await route.continue_(post_data=json.dumps(body))
                    return
                except Exception as e:
                    logger.error(f"Request modify error: {e}")
            await route.continue_()
        
        async def on_response(response):
            """Capture the SSE response from the chat endpoint."""
            if "/duckchat/v1/chat" not in response.url:
                return
            if response.request.method != "POST":
                return
                
            try:
                body = await response.body()
                text = body.decode('utf-8', errors='replace')
                logger.info(f"Response captured: status={response.status}, len={len(text)}")
                
                if response.status == 200:
                    for line in text.split('\n'):
                        line = line.strip()
                        if line.startswith('data: '):
                            payload = line[6:]
                            if payload == '[DONE]':
                                continue
                            try:
                                chunk = json.loads(payload)
                                msg = chunk.get('message', '')
                                if msg:
                                    response_chunks.append(msg)
                            except json.JSONDecodeError:
                                pass
            except Exception as e:
                logger.error(f"Response capture error: {e}")
            finally:
                response_done.set()
        
        await browser.page.route("**/duckchat/v1/chat", modify_request)
        browser.page.on("response", on_response)
        
        # Navigate to fresh duck.ai page
        await browser.goto("https://duck.ai/")
        await asyncio.sleep(3)
        
        # Dismiss "Got It!" popup
        for _ in range(3):
            try:
                got_it = browser.page.locator("button:has-text('Got It!')")
                if await got_it.count() > 0 and await got_it.is_visible():
                    await got_it.click()
                    logger.info("Dismissed 'Got It!' popup")
                    await asyncio.sleep(0.5)
                    break
            except: pass
        
        # Type message
        textarea = browser.page.locator("textarea")
        try:
            await textarea.wait_for(state="visible", timeout=5000)
        except:
            logger.error("Textarea not visible!")
            return ""
        
        await textarea.click()
        await asyncio.sleep(0.3)
        await textarea.fill(user_msg[:500])
        await asyncio.sleep(0.3)
        
        # NOW activate interception (only for the actual send)
        intercept_active = True
        
        # Send
        sent = False
        for btn_text in ['Ask', 'Send']:
            try:
                btn = browser.page.locator(f"button:has-text('{btn_text}')")
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    sent = True
                    logger.info(f"Clicked '{btn_text}'")
                    break
            except: pass
        if not sent:
            await textarea.press("Enter")
            logger.info("Pressed Enter")
        
        # Wait for response
        try:
            await asyncio.wait_for(response_done.wait(), timeout=40)
        except asyncio.TimeoutError:
            logger.warning("Response timed out after 40s")
        
        await asyncio.sleep(0.5)
        
        # Cleanup
        intercept_active = False
        try:
            await browser.page.unroute("**/duckchat/v1/chat")
        except: pass
        browser.page.remove_listener("response", on_response)
        
        result = ''.join(response_chunks).strip()
        logger.info(f"DDG result ({len(result)} chars): {result[:100]}...")
        return result


async def close():
    global _browser
    if _browser:
        from sdk.utils.browser import close_browser
        try:
            await close_browser("ddg-prod")
        except: pass
        _browser = None


