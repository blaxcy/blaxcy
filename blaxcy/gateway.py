from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GatewayEnvelope:
    """Transport-neutral ChatGPT/device message.

    A real network gateway can carry these envelopes without changing
    the device control protocol.
    """

    direction: str
    message: dict[str, Any]

    def encode(self) -> str:
        return json.dumps({
            "protocol": "blaxcy/gateway/0.1",
            "direction": self.direction,
            "message": self.message,
        }, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def decode(cls, raw: str) -> "GatewayEnvelope":
        data = json.loads(raw)
        if data.get("protocol") != "blaxcy/gateway/0.1":
            raise ValueError("unsupported gateway protocol")
        direction = data.get("direction")
        message = data.get("message")
        if direction not in {"device->chatgpt", "chatgpt->device"} or not isinstance(message, dict):
            raise ValueError("invalid gateway envelope")
        return cls(direction, message)
