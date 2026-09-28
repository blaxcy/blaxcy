from __future__ import annotations

from typing import Any

from .keyboard import hotkey, press, type_text
from .mouse import click, move, scroll


class CommandError(ValueError):
    pass


def execute(command: dict[str, Any], screen_width: int, screen_height: int) -> dict[str, Any]:
    if command.get("type") != "command":
        raise CommandError("expected type=command")

    action = command.get("action")
    if action == "mouse.move":
        x, y = _xy(command, screen_width, screen_height)
        move(x, y)
    elif action == "mouse.click":
        x, y = _xy(command, screen_width, screen_height)
        click(x, y, str(command.get("button", "left")), int(command.get("clicks", 1)))
    elif action == "mouse.scroll":
        x, y = _xy(command, screen_width, screen_height)
        amount = int(command.get("amount", 0))
        if abs(amount) > 100:
            raise CommandError("scroll amount too large")
        scroll(x, y, amount)
    elif action == "keyboard.press":
        press(_key(command))
    elif action == "keyboard.hotkey":
        keys = command.get("keys")
        if not isinstance(keys, list) or not keys or len(keys) > 6:
            raise CommandError("invalid hotkey")
        hotkey(*(str(k) for k in keys))
    elif action == "keyboard.type":
        value = command.get("text")
        if not isinstance(value, str) or len(value) > 10000:
            raise CommandError("invalid text")
        type_text(value)
    else:
        raise CommandError(f"unsupported action: {action}")

    return {"ok": True, "action": action}


def _xy(command: dict[str, Any], sw: int, sh: int) -> tuple[int, int]:
    try:
        x, y = int(command["x"]), int(command["y"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CommandError("x/y required") from exc
    if not (0 <= x < sw and 0 <= y < sh):
        raise CommandError("coordinates outside screen")
    return x, y


def _key(command: dict[str, Any]) -> str:
    key = command.get("key")
    if not isinstance(key, str) or not 1 <= len(key) <= 32:
        raise CommandError("invalid key")
    return key
