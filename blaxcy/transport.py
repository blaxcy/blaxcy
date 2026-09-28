from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable

import websockets
from websockets.server import ServerConnection

from .commands import CommandError, execute


class LocalTransport:
    """Authenticated localhost WebSocket control channel.

    This is intentionally foreground-only and binds to loopback by default.
    """

    def __init__(
        self,
        token: str,
        state_provider: Callable[[], dict[str, Any]],
        screen_size: Callable[[], tuple[int, int]],
    ):
        self.token = token
        self.state_provider = state_provider
        self.screen_size = screen_size

    async def handler(self, ws: ServerConnection) -> None:
        authenticated = False
        async for raw in ws:
            try:
                msg = json.loads(raw)
                if not isinstance(msg, dict):
                    raise ValueError("object required")

                if not authenticated:
                    if msg.get("type") != "auth" or msg.get("token") != self.token:
                        await ws.send(json.dumps({"ok": False, "error": "unauthorized"}))
                        await ws.close(code=1008)
                        return
                    authenticated = True
                    await ws.send(json.dumps({"ok": True, "type": "auth.ok"}))
                    continue

                if msg.get("type") == "state.get":
                    await ws.send(json.dumps({"ok": True, "type": "state", "state": self.state_provider()}))
                    continue

                if msg.get("type") == "command":
                    sw, sh = self.screen_size()
                    result = execute(msg, sw, sh)
                    await ws.send(json.dumps(result))
                    continue

                raise ValueError("unknown message")
            except (ValueError, CommandError) as exc:
                await ws.send(json.dumps({"ok": False, "error": str(exc)}))

    async def serve(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        async with websockets.serve(self.handler, host, port, max_size=2**20):
            await asyncio.Future()


def run_server(transport: LocalTransport, host: str, port: int) -> None:
    asyncio.run(transport.serve(host, port))
