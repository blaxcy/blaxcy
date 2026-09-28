from __future__ import annotations

import json
import secrets
import time
from typing import Any


def session_token() -> str:
    return secrets.token_urlsafe(32)


def event(event_type: str, **payload: Any) -> dict[str, Any]:
    return {
        "protocol": "blaxcy/0.1",
        "ts": time.time_ns(),
        "type": event_type,
        **payload,
    }


def encode(message: dict[str, Any]) -> str:
    return json.dumps(message, separators=(",", ":"), ensure_ascii=False)


def decode(message: str) -> dict[str, Any]:
    value = json.loads(message)
    if not isinstance(value, dict):
        raise ValueError("protocol message must be an object")
    return value
