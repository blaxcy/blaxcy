from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScreenState:
    width: int
    height: int
    revision: int = 0
    elements: list[dict[str, Any]] = field(default_factory=list)
    cursor: dict[str, int] | None = None
    last_frame_hash: str | None = None

    def keyframe(self) -> dict[str, Any]:
        return {
            "type": "eye.keyframe",
            "revision": self.revision,
            "screen": {"width": self.width, "height": self.height},
            "elements": self.elements,
            "cursor": self.cursor,
        }

    def apply_delta(self, delta: dict[str, Any]) -> None:
        self.revision = int(delta["revision"])
        if "elements" in delta:
            self.elements = delta["elements"]
        if "cursor" in delta:
            self.cursor = delta["cursor"]
