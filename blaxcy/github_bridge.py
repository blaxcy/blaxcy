from __future__ import annotations

"""GitHub-file control bridge.

The device publishes a machine-readable snapshot to a repository file and
polls a command file for instructions. This is intentionally explicit:
commands are schema-validated, bounded, authenticated by a per-install secret,
and acknowledged in the state file.
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from .commands import CommandError, execute

STATE_PATH = Path(os.getenv("BLAXCY_STATE_FILE", ".blaxcy/screen_state.json"))
COMMAND_PATH = Path(os.getenv("BLAXCY_COMMAND_FILE", ".blaxcy/command.json"))
ACK_PATH = Path(os.getenv("BLAXCY_ACK_FILE", ".blaxcy/command_ack.json"))
SECRET_PATH = Path(os.getenv("BLAXCY_SECRET_FILE", ".blaxcy/device_secret"))

MAX_TEXT = 4000


def _secret() -> str:
    SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SECRET_PATH.exists():
        import secrets
        SECRET_PATH.write_text(secrets.token_urlsafe(32), encoding="utf-8")
        try:
            SECRET_PATH.chmod(0o600)
        except OSError:
            pass
    return SECRET_PATH.read_text(encoding="utf-8").strip()


def command_signature(command: dict[str, Any]) -> str:
    raw = json.dumps(command, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((_secret() + raw).encode()).hexdigest()


def write_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(STATE_PATH)


def read_command() -> dict[str, Any] | None:
    if not COMMAND_PATH.exists():
        return None
    try:
        obj = json.loads(COMMAND_PATH.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def acknowledge(command_id: str, ok: bool, result: Any = None, error: str | None = None) -> None:
    ACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "protocol": "blaxcy/github-bridge/0.1",
        "command_id": command_id,
        "ok": ok,
        "ts_ns": time.time_ns(),
    }
    if ok:
        payload["result"] = result
    else:
        payload["error"] = error
    ACK_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def validate(command: dict[str, Any]) -> None:
    if command.get("signature") != command_signature({k: v for k, v in command.items() if k != "signature"}):
        raise CommandError("invalid command signature")
    if not isinstance(command.get("id"), str) or len(command["id"]) > 128:
        raise CommandError("invalid command id")
    if command.get("action") not in {
        "mouse.move", "mouse.click", "mouse.scroll",
        "keyboard.press", "keyboard.hotkey", "keyboard.type",
    }:
        raise CommandError("unsupported action")
    if command.get("action") == "keyboard.type" and len(str(command.get("text", ""))) > MAX_TEXT:
        raise CommandError("text payload too large")


def process_once(screen_width: int, screen_height: int, last_id: str | None) -> str | None:
    command = read_command()
    if not command:
        return last_id
    cid = str(command.get("id", ""))
    if not cid or cid == last_id:
        return last_id
    try:
        validate(command)
        result = execute(command, screen_width, screen_height)
        acknowledge(cid, True, result=result)
    except (CommandError, ValueError) as exc:
        acknowledge(cid, False, error=str(exc))
    return cid
