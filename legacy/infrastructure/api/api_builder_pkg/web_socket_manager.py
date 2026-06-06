
"""
api_builder_pkg/web_socket_manager.py — WebSocketManager
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class WebSocketManager:
    """Production WebSocket manager for real-time model streaming.

    Protocol:
      Client → Server:
        {"type": "auth", "api_key": "ark_xxx"}
        {"type": "chat", "model": "gemini-pro", "messages": [...], "stream": true}
        {"type": "subscribe", "channel": "model_events"}
        {"type": "unsubscribe", "channel": "model_events"}
        {"type": "ping"}

      Server → Client:
        {"type": "auth_ok", "connection_id": "abc123", "tier": "basic"}
        {"type": "auth_error", "message": "Invalid API key"}
        {"type": "chunk", "request_id": "xxx", "content": "...", "done": false}
        {"type": "chunk", "request_id": "xxx", "content": "", "done": true, "usage": {...}}
        {"type": "event", "channel": "model_events", "data": {...}}
        {"type": "pong", "server_time": 1234567890.0}
        {"type": "error", "message": "...", "request_id": "xxx"}
    """

    HEARTBEAT_INTERVAL = 30  # seconds
    MAX_CONNECTIONS_PER_USER = 5
    MAX_MESSAGE_SIZE = 1_048_576  # 1MB
    IDLE_TIMEOUT = 300  # 5 minutes

    def __init__(self, api_builder: "APIBuilderAgent"):
        self._builder = api_builder
        self._connections: Dict[str, WebSocketConnection] = {}
        self._user_connections: Dict[str, Set[str]] = defaultdict(set)
        self._channels: Dict[str, Set[str]] = defaultdict(set)  # channel → {conn_ids}
        self._total_messages = 0
        self._total_connections = 0
        self._started_at = time.time()
        self._send_fn: Dict[str, Callable] = {}  # conn_id → send function
        self._close_fn: Dict[str, Callable] = {}  # conn_id → close function

    @property
    def active_connections(self) -> int:
        return sum(1 for c in self._connections.values() if c.is_alive)

    def register_connection(self, conn_id: str, send_fn: Callable, close_fn: Callable) -> WebSocketConnection:
        """Register a new WebSocket connection with its send/close callbacks.

        Args:
            conn_id: Unique connection identifier
            send_fn: async callable(dict) to send JSON to client
            close_fn: async callable() to close the connection
        """
        conn = WebSocketConnection(conn_id=conn_id)
        self._connections[conn_id] = conn
        self._send_fn[conn_id] = send_fn
        self._close_fn[conn_id] = close_fn
        self._total_connections += 1
        logger.info("WebSocket connection registered: %s", conn_id)
        return conn

    def unregister_connection(self, conn_id: str):
        """Clean up a closed connection."""
        conn = self._connections.pop(conn_id, None)
        if conn:
            conn._closed = True
            self._user_connections.get(conn.user_id, set()).discard(conn_id)
            # Remove from all channels
            for channel_conns in self._channels.values():
                channel_conns.discard(conn_id)
        self._send_fn.pop(conn_id, None)
        self._close_fn.pop(conn_id, None)
        logger.info("WebSocket connection closed: %s", conn_id)

    async def _send(self, conn_id: str, message: Dict[str, Any]) -> bool:
        """Send a JSON message to a connection. Returns False if failed."""
        send_fn = self._send_fn.get(conn_id)
        if not send_fn:
            return False
        try:
            data = json.dumps(message, ensure_ascii=False)
            await send_fn(message)
            conn = self._connections.get(conn_id)
            if conn:
                conn.mark_activity(bytes_out=len(data))
            return True
        except Exception as e:
            logger.warning("WebSocket send failed for %s: %s", conn_id, e)
            return False

    async def handle_message(self, conn_id: str, raw_message: str) -> Optional[Dict]:
        """Process an incoming WebSocket message.

        Returns response dict (also sent via send_fn), or None.
        """
        conn = self._connections.get(conn_id)
        if not conn or conn._closed:
            return {"type": "error", "message": "Connection not found"}

        if len(raw_message) > self.MAX_MESSAGE_SIZE:
            resp = {"type": "error", "message": f"Message too large (max {self.MAX_MESSAGE_SIZE} bytes)"}
            await self._send(conn_id, resp)
            return resp

        try:
            msg = json.loads(raw_message)
        except json.JSONDecodeError:
            resp = {"type": "error", "message": "Invalid JSON"}
            await self._send(conn_id, resp)
            return resp

        conn.mark_activity(bytes_in=len(raw_message))
        self._total_messages += 1
        msg_type = msg.get("type", "")

        if msg_type == "auth":
            return await self._handle_auth(conn, msg)
        elif msg_type == "ping":
            return await self._handle_ping(conn)
        elif msg_type == "chat":
            return await self._handle_chat(conn, msg)
        elif msg_type == "subscribe":
            return await self._handle_subscribe(conn, msg)
        elif msg_type == "unsubscribe":
            return await self._handle_unsubscribe(conn, msg)
        else:
            resp = {"type": "error", "message": f"Unknown message type: {msg_type}"}
            await self._send(conn.conn_id, resp)
            return resp

    async def _handle_auth(self, conn: WebSocketConnection, msg: Dict) -> Dict:
        """Authenticate a WebSocket connection."""
        api_key = msg.get("api_key", "")
        ok, info = self._builder.auth.validate(api_key, AuthLevel.BASIC)

        if not ok:
            resp = {"type": "auth_error", "message": "Invalid or insufficient API key"}
            await self._send(conn.conn_id, resp)
            return resp

        conn.user_id = info["user_id"]
        conn.tier = info["tier"]

        # Enforce per-user connection limit
        user_conns = self._user_connections[conn.user_id]
        if len(user_conns) >= self.MAX_CONNECTIONS_PER_USER:
            resp = {"type": "auth_error",
                    "message": f"Too many connections (max {self.MAX_CONNECTIONS_PER_USER})"}
            await self._send(conn.conn_id, resp)
            return resp

        user_conns.add(conn.conn_id)
        resp = {
            "type": "auth_ok",
            "connection_id": conn.conn_id,
            "user_id": conn.user_id,
            "tier": conn.tier,
        }
        await self._send(conn.conn_id, resp)
        logger.info("WebSocket authenticated: %s → user=%s tier=%s",
                     conn.conn_id, conn.user_id, conn.tier)
        return resp

    async def _handle_ping(self, conn: WebSocketConnection) -> Dict:
        """Respond to heartbeat ping."""
        conn.last_heartbeat = time.time()
        resp = {"type": "pong", "server_time": time.time()}
        await self._send(conn.conn_id, resp)
        return resp

    async def _handle_chat(self, conn: WebSocketConnection, msg: Dict) -> Dict:
        """Handle a chat request — stream model response via WebSocket."""
        if conn.user_id == "anonymous":
            resp = {"type": "error", "message": "Authentication required before chat"}
            await self._send(conn.conn_id, resp)
            return resp

        request_id = uuid.uuid4().hex[:12]
        model_key = msg.get("model", "gemini-pro")
        messages = msg.get("messages", [])
        stream = msg.get("stream", True)

        if not messages:
            prompt = msg.get("prompt", "")
            if prompt:
                messages = [{"role": "user", "content": prompt}]
            else:
                resp = {"type": "error", "request_id": request_id,
                        "message": "No messages or prompt provided"}
                await self._send(conn.conn_id, resp)
                return resp

        # Rate limit check
        provider = "openrouter"
        try:
            from arki_project.utils.models_registry import get_model as _ws_get_model
            _m = _ws_get_model(model_key)
            provider = _m.provider
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)

        rate_ok, rate_info = self._builder.rate_limiter.check(conn.user_id, model_key, provider)
        if not rate_ok:
            resp = {
                "type": "error",
                "request_id": request_id,
                "message": "Rate limit exceeded",
                "retry_after_seconds": rate_info.get("retry_after_seconds", 60) if rate_info else 60,
            }
            await self._send(conn.conn_id, resp)
            return resp

        # Send acknowledgment
        await self._send(conn.conn_id, {
            "type": "chat_ack",
            "request_id": request_id,
            "model": model_key,
        })

        # Execute the model call
        t0 = time.time()
        try:
            # System prompt from message or default
            sys_prompt = msg.get("system_prompt", "")
            if sys_prompt:
                messages.insert(0, {"role": "system", "content": sys_prompt})

            response = await self._builder.quick_chat(
                model_key,
                messages[-1]["content"] if messages else "",
                system_prompt=sys_prompt,
                temperature=msg.get("temperature", 0.7),
                max_tokens=msg.get("max_tokens", 65536),
            )
            latency_ms = (time.time() - t0) * 1000
            tokens_est = len(response) // 4

            if stream:
                # Simulate streaming by chunking the response
                chunk_size = max(20, len(response) // 10)
                for i in range(0, len(response), chunk_size):
                    chunk = response[i:i + chunk_size]
                    await self._send(conn.conn_id, {
                        "type": "chunk",
                        "request_id": request_id,
                        "content": chunk,
                        "done": False,
                    })
                    await asyncio.sleep(0.01)  # Small delay between chunks

            # Final chunk with done=True
            final = {
                "type": "chunk",
                "request_id": request_id,
                "content": "" if stream else response,
                "done": True,
                "usage": {
                    "model": model_key,
                    "estimated_tokens": tokens_est,
                    "latency_ms": round(latency_ms, 1),
                },
            }
            await self._send(conn.conn_id, final)

            self._builder.router.record_latency(model_key, latency_ms)
            return final

        except asyncio.TimeoutError:
            resp = {"type": "error", "request_id": request_id,
                    "message": f"Model {model_key} timed out"}
            await self._send(conn.conn_id, resp)
            return resp
        except Exception as e:
            resp = {"type": "error", "request_id": request_id,
                    "message": str(e)}
            await self._send(conn.conn_id, resp)
            return resp

    async def _handle_subscribe(self, conn: WebSocketConnection, msg: Dict) -> Dict:
        """Subscribe to a real-time event channel."""
        channel = msg.get("channel", "")
        valid_channels = {"model_events", "health", "rate_limits", "errors"}
        if channel not in valid_channels:
            resp = {"type": "error",
                    "message": f"Invalid channel. Valid: {', '.join(sorted(valid_channels))}"}
            await self._send(conn.conn_id, resp)
            return resp

        self._channels[channel].add(conn.conn_id)
        conn.subscriptions.add(channel)
        resp = {"type": "subscribed", "channel": channel}
        await self._send(conn.conn_id, resp)
        return resp

    async def _handle_unsubscribe(self, conn: WebSocketConnection, msg: Dict) -> Dict:
        """Unsubscribe from a channel."""
        channel = msg.get("channel", "")
        self._channels.get(channel, set()).discard(conn.conn_id)
        conn.subscriptions.discard(channel)
        resp = {"type": "unsubscribed", "channel": channel}
        await self._send(conn.conn_id, resp)
        return resp

    async def broadcast(self, channel: str, data: Dict[str, Any]):
        """Broadcast an event to all subscribers of a channel."""
        conn_ids = self._channels.get(channel, set()).copy()
        message = {"type": "event", "channel": channel, "data": data, "timestamp": time.time()}
        dead = []
        for cid in conn_ids:
            if not await self._send(cid, message):
                dead.append(cid)
        # Cleanup dead connections
        for cid in dead:
            self.unregister_connection(cid)

    async def cleanup_idle(self):
        """Remove idle/dead connections. Call periodically."""
        now = time.time()
        dead = []
        for conn_id, conn in self._connections.items():
            if not conn.is_alive:
                dead.append(conn_id)
            elif (now - conn.last_activity) > self.IDLE_TIMEOUT:
                dead.append(conn_id)
                await self._send(conn_id, {"type": "error", "message": "Idle timeout"})
        for cid in dead:
            close_fn = self._close_fn.get(cid)
            if close_fn:
                try:
                    await close_fn()
                except Exception as _err:
                    logger.warning("Suppressed error: %s", _err)
            self.unregister_connection(cid)
        if dead:
            logger.info("WebSocket cleanup: removed %d idle/dead connections", len(dead))

    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics."""
        alive = [c for c in self._connections.values() if c.is_alive]
        return {
            "active_connections": len(alive),
            "total_connections_served": self._total_connections,
            "total_messages_processed": self._total_messages,
            "uptime_seconds": round(time.time() - self._started_at, 1),
            "channels": {ch: len(conns) for ch, conns in self._channels.items() if conns},
            "connections": [
                {
                    "conn_id": c.conn_id,
                    "user_id": c.user_id,
                    "tier": c.tier,
                    "connected_seconds": round(time.time() - c.connected_at, 1),
                    "messages": c.message_count,
                    "subscriptions": list(c.subscriptions),
                }
                for c in alive
            ],
        }

# ═══════════════════════════════════════════════════════════════════
# API Builder Agent — The Main Engine
# ═══════════════════════════════════════════════════════════════════




# ═══════════════════════════════════════════════════════════════════
# Rate Limiter — Token Bucket per model per user
# ═══════════════════════════════════════════════════════════════════



