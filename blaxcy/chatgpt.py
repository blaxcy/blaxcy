from __future__ import annotations

from typing import Any

CAPABILITIES = {
    "eye": {
        "state": "eye_state",
        "snapshot": "eye_snapshot",
        "events": "eye_events",
    },
    "mouse": {
        "move": "mouse_move",
        "click": "mouse_click",
        "scroll": "mouse_scroll",
    },
    "keyboard": {
        "press": "keyboard_press",
        "hotkey": "keyboard_hotkey",
        "type": "keyboard_type",
    },
}


def tool_manifest() -> dict[str, Any]:
    """Machine-readable interface exposed by the repo's MCP connector."""
    return {
        "protocol": "blaxcy/chatgpt/0.2",
        "capabilities": CAPABILITIES,
        "visual_output": "mcp-image",
        "incremental_eye_events": True,
        "commands_are_structured": True,
        "arbitrary_shell": False,
    }
