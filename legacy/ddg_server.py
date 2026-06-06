
"""
DDG AI Chat HTTP Server
Wraps the browser-based DDG provider as a simple HTTP API.
Run with coworker-deps python (has playwright).
Bot calls this via localhost HTTP.
"""
import asyncio
import json
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Global provider state
_ddg_loop = None
_ddg_ready = False

class DDGHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/chat':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            messages = data.get('messages', [])
            model = data.get('model', 'gpt-4o-mini')
            
            # Run async DDG chat in the event loop
            future = asyncio.run_coroutine_threadsafe(
                _do_chat(messages, model), _ddg_loop
            )
            try:
                result = future.result(timeout=45)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'text': result}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        elif self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        print(f"[DDG Server] {args[0]}", flush=True)


async def _do_chat(messages, model):
    from utils.ddg_provider import ddg_chat
    return await ddg_chat(messages, model)


def run_server(port=9876):
    server = HTTPServer(('127.0.0.1', port), DDGHandler)
    print(f"[DDG Server] Listening on http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


async def _async_main():
    global _ddg_loop, _ddg_ready
    _ddg_loop = asyncio.get_event_loop()
    
    # Start HTTP server in a thread
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    _ddg_ready = True
    
    # Keep running
    while True:
        await asyncio.sleep(3600)


if __name__ == '__main__':
    asyncio.run(_async_main())


