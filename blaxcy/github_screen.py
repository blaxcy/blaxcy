from __future__ import annotations

"""Build a ChatGPT-readable screen snapshot from the EYE state.

The file is a semantic snapshot, not a raw video stream. It contains screen
geometry, cursor, visible UI elements, changed regions, and a compact visual
reference. A fresh snapshot replaces the previous one atomically.
"""

import base64
import hashlib
import json
from pathlib import Path
from typing import Any


def make_snapshot(
    *,
    width: int,
    height: int,
    revision: int,
    cursor: dict[str, int],
    elements: list[dict[str, Any]],
    changed_regions: list[dict[str, int]] | None = None,
    frame_bytes: bytes | None = None,
) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "protocol": "blaxcy/screen/0.2",
        "revision": revision,
        "screen": {"width": width, "height": height},
        "cursor": cursor,
        "elements": elements,
        "changed_regions": changed_regions or [],
    }
    if frame_bytes:
        # Keep this opt-in and bounded; GitHub is not a video transport.
        snapshot["frame"] = {
            "encoding": "base64",
            "sha256": hashlib.sha256(frame_bytes).hexdigest(),
            "data": base64.b64encode(frame_bytes).decode(),
        }
    return snapshot


def write_snapshot(path: str | Path, snapshot: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
