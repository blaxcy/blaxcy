from __future__ import annotations

import asyncio
import atexit
import json
import os
import subprocess
import sys
import time
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Image

_runtime_process: subprocess.Popen | None = None


mcp = MCPServer(
    "BLAXCY",
    instructions=(
        "BLAXCY controls the foreground user's own device. "
        "Use eye_state or eye_snapshot before acting; prefer semantic element coordinates; "
        "never execute arbitrary shell commands."
    ),
)


def _load_pairing() -> dict[str, Any]:
    path = os.environ.get("BLAXCY_PAIRING_FILE", ".blaxcy/pairing.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _ws_url() -> str:
    return os.environ.get("BLAXCY_WS", "ws://127.0.0.1:8765")


async def _runtime_reachable() -> bool:
    try:
        import websockets
        pairing = _load_pairing()
        async with websockets.connect(_ws_url(), open_timeout=0.5, close_timeout=0.5) as ws:
            await ws.send(json.dumps({"type": "auth", "token": pairing["token"]}))
            response = json.loads(await asyncio.wait_for(ws.recv(), timeout=0.8))
            return bool(response.get("ok"))
    except Exception:
        return False


async def _ensure_runtime() -> None:
    global _runtime_process
    if await _runtime_reachable():
        return
    if _runtime_process is None or _runtime_process.poll() is not None:
        pairing_file = os.environ.get("BLAXCY_PAIRING_FILE", ".blaxcy/pairing.json")
        _runtime_process = subprocess.Popen(
            [
                sys.executable, "-m", "blaxcy", "connect",
                "--quiet", "--pairing-file", pairing_file,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        if await _runtime_reachable():
            return
        await asyncio.sleep(0.2)
    raise RuntimeError("BLAXCY foreground runtime did not become reachable")


def _stop_runtime() -> None:
    global _runtime_process
    if _runtime_process is not None and _runtime_process.poll() is None:
        _runtime_process.terminate()
        try:
            _runtime_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            _runtime_process.kill()


atexit.register(_stop_runtime)


async def _request(message: dict[str, Any]) -> dict[str, Any]:
    await _ensure_runtime()
    import websockets

    pairing = _load_pairing()
    token = pairing["token"]
    async with websockets.connect(_ws_url(), max_size=8 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"type": "auth", "token": token}))
        auth = json.loads(await ws.recv())
        if not auth.get("ok"):
            raise RuntimeError("BLAXCY authentication failed")
        await ws.recv()  # initial state
        await ws.send(json.dumps(message))
        return json.loads(await ws.recv())


def _image_from_state(state: dict[str, Any]) -> Image | None:
    image = state.get("image")
    if not isinstance(image, dict) or image.get("encoding") != "jpeg":
        return None
    try:
        import base64
        return Image(data=base64.b64decode(image["data"]), format="jpeg")
    except Exception:
        return None


@mcp.tool()
async def eye_state() -> dict[str, Any]:
    """Return the latest EYE semantic state, cursor, revision and frame hash."""
    return await _request({"type": "state.get"})


@mcp.tool()
async def eye_snapshot() -> Image | str:
    """Return the latest EYE keyframe as an image for visual inspection."""
    result = await _request({"type": "state.get"})
    state = result.get("state", {})
    image = _image_from_state(state)
    if image is not None:
        return image
    return "No visual keyframe is currently available."


@mcp.tool()
async def eye_events(since_revision: int = 0, limit: int = 64) -> dict[str, Any]:
    """Return EYE deltas/cursor/keyframes after a revision for incremental perception."""
    return await _request({
        "type": "events.get",
        "revision": max(0, since_revision),
        "limit": max(1, min(limit, 256)),
    })


@mcp.tool()
async def mouse_move(x: int, y: int) -> dict[str, Any]:
    """Move the mouse to screen coordinates."""
    return await _request({"type": "command", "action": "mouse.move", "x": x, "y": y})


@mcp.tool()
async def mouse_click(
    x: int,
    y: int,
    button: str = "left",
    clicks: int = 1,
) -> dict[str, Any]:
    """Click at screen coordinates."""
    return await _request({
        "type": "command",
        "action": "mouse.click",
        "x": x,
        "y": y,
        "button": button,
        "clicks": clicks,
    })


@mcp.tool()
async def mouse_scroll(amount: int) -> dict[str, Any]:
    """Scroll the foreground device."""
    return await _request({"type": "command", "action": "mouse.scroll", "amount": amount})


@mcp.tool()
async def keyboard_press(key: str) -> dict[str, Any]:
    """Press one keyboard key."""
    return await _request({"type": "command", "action": "keyboard.press", "key": key})


@mcp.tool()
async def keyboard_hotkey(keys: list[str]) -> dict[str, Any]:
    """Press a keyboard shortcut."""
    return await _request({"type": "command", "action": "keyboard.hotkey", "keys": keys})


@mcp.tool()
async def keyboard_type(text: str) -> dict[str, Any]:
    """Type text into the focused control."""
    return await _request({"type": "command", "action": "keyboard.type", "text": text})


def main() -> None:
    transport = os.environ.get("BLAXCY_MCP_TRANSPORT", "stdio")
    if transport == "streamable-http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
