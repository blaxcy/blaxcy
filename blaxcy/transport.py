from __future__ import annotations

import asyncio
import hmac
import json
import threading
from collections import deque
from typing import Any, Callable

import websockets
from websockets.server import ServerConnection

from .commands import CommandError, execute


class LocalTransport:
    """Authenticated loopback WebSocket channel with live EYE broadcasts and replayable deltas."""

    def __init__(
        self,
        token: str,
        state_provider: Callable[[], dict[str, Any]],
        screen_size: Callable[[], tuple[int, int]],
        history_size: int = 256,
    ):
        self.token = token
        self.state_provider = state_provider
        self.screen_size = screen_size
        self._clients: set[ServerConnection] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()
        self._history: deque[dict[str, Any]] = deque(maxlen=history_size)
        self._history_lock = threading.Lock()

    def publish(self, message: dict[str, Any]) -> None:
        with self._history_lock:
            self._history.append(message)
        loop = self._loop
        if loop is not None and loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast(message), loop)

    def events_since(self, revision: int, limit: int = 64) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 256))
        with self._history_lock:
            return [
                item for item in self._history
                if int(item.get("revision", 0)) > int(revision)
            ][-limit:]

    async def _broadcast(self, message: dict[str, Any]) -> None:
        if not self._clients:
            return
        payload = json.dumps(message, separators=(",", ":"), ensure_ascii=False)
        clients = tuple(self._clients)
        results = await asyncio.gather(
            *(client.send(payload) for client in clients),
            return_exceptions=True,
        )
        for client, result in zip(clients, results):
            if isinstance(result, Exception):
                self._clients.discard(client)

    async def handler(self, ws: ServerConnection) -> None:
        authenticated = False
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    if not isinstance(msg, dict):
                        raise ValueError("object required")

                    if not authenticated:
                        supplied = str(msg.get("token", ""))
                        if msg.get("type") != "auth" or not hmac.compare_digest(supplied, self.token):
                            await ws.send(json.dumps({"ok": False, "error": "unauthorized"}))
                            await ws.close(code=1008)
                            return
                        authenticated = True
                        self._clients.add(ws)
                        await ws.send(json.dumps({"ok": True, "type": "auth.ok"}))
                        await ws.send(json.dumps({
                            "ok": True,
                            "type": "state",
                            "state": self.state_provider(),
                        }))
                        continue

                    message_type = msg.get("type")
                    if message_type == "state.get":
                        await ws.send(json.dumps({
                            "ok": True,
                            "type": "state",
                            "state": self.state_provider(),
                        }))
                        continue

                    if message_type == "events.get":
                        revision = int(msg.get("revision", 0))
                        limit = int(msg.get("limit", 64))
                        await ws.send(json.dumps({
                            "ok": True,
                            "type": "events",
                            "events": self.events_since(revision, limit),
                        }))
                        continue

                    if message_type == "command":
                        sw, sh = self.screen_size()
                        result = execute(msg, sw, sh)
                        await ws.send(json.dumps(result))
                        continue

                    raise ValueError("unknown message")
                except (ValueError, CommandError) as exc:
                    await ws.send(json.dumps({"ok": False, "error": str(exc)}))
        finally:
            self._clients.discard(ws)

    async def serve(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self._loop = asyncio.get_running_loop()
        self._ready.set()
        async with websockets.serve(
            self.handler,
            host,
            port,
            max_size=8 * 1024 * 1024,
        ):
            await asyncio.Future()

    def wait_ready(self, timeout: float = 5.0) -> bool:
        return self._ready.wait(timeout)
