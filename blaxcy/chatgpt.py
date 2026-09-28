from __future__ import annotations

from typing import Any

CAPABILITIES = {
    "eye": {
        "state": "eye.state",
        "subscribe": "eye.subscribe",
    },
    "mouse": {
        "move": "mouse.move",
        "click": "mouse.click",
        "scroll": "mouse.scroll",
    },
    "keyboard": {
        "press": "keyboard.press",
        "hotkey": "keyboard.hotkey",
        "type": "keyboard.type",
    },
}


def tool_manifest() -> dict[str, Any]:
    """Machine-readable interface for a ChatGPT connector."""
    return {
        "protocol": "blaxcy/chatgpt/0.1",
        "capabilities": CAPABILITIES,
        "commands_are_structured": True,
        "arbitrary_shell": False,
    }
