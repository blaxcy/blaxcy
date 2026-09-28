from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from .accessibility import AccessibilityProvider


@dataclass
class SemanticConfig:
    ocr: bool = False
    accessibility: bool = True
    max_elements: int = 500


class SemanticAnalyzer:
    """Multi-source semantic perception: native UI tree + OCR + geometry."""

    def __init__(self, config: SemanticConfig | None = None):
        self.config = config or SemanticConfig()
        self.accessibility = AccessibilityProvider()

    @staticmethod
    def _stable_id(element: dict[str, Any]) -> str:
        identity = "|".join([
            str(element.get("type", "")),
            str(element.get("role", "")),
            str(element.get("name", element.get("text", ""))).strip(),
            str(int(element.get("x", 0))),
            str(int(element.get("y", 0))),
            str(int(element.get("width", 0))),
            str(int(element.get("height", 0))),
        ])
        return "e_" + hashlib.blake2s(identity.encode("utf-8"), digest_size=6).hexdigest()

    def analyze(self, frame_bgr: np.ndarray) -> list[dict[str, Any]]:
        elements: list[dict[str, Any]] = []
        if self.config.accessibility:
            elements.extend(self.accessibility.snapshot())
        if self.config.ocr:
            elements.extend(self._ocr(frame_bgr))

        normalized: list[dict[str, Any]] = []
        seen: set[tuple[str, int, int, int, int, str]] = set()
        for element in elements:
            x = int(element.get("x", 0))
            y = int(element.get("y", 0))
            w = max(0, int(element.get("width", 0)))
            h = max(0, int(element.get("height", 0)))
            name = str(element.get("name", element.get("text", ""))).strip()
            key = (str(element.get("type", "")), x, y, w, h, name)
            if w <= 0 or h <= 0 or key in seen:
                continue
            seen.add(key)
            normalized.append({
                **element,
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "confidence": float(element.get("confidence", 0.95)),
            })

        for element in normalized[: self.config.max_elements]:
            element["id"] = self._stable_id(element)
            element["screen"] = {
                "x": element["x"],
                "y": element["y"],
                "width": element["width"],
                "height": element["height"],
            }
        return normalized

    def _ocr(self, frame_bgr: np.ndarray) -> list[dict[str, Any]]:
        try:
            import pytesseract
        except ImportError:
            return []
        data = pytesseract.image_to_data(
            cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB),
            output_type=pytesseract.Output.DICT,
            config="--psm 6",
        )
        result: list[dict[str, Any]] = []
        for i, text in enumerate(data.get("text", [])):
            value = str(text).strip()
            try:
                conf = float(data["conf"][i])
            except (TypeError, ValueError):
                conf = -1
            if not value or conf < 20:
                continue
            result.append({
                "type": "text",
                "text": value,
                "confidence": round(conf / 100.0, 3),
                "x": int(data["left"][i]),
                "y": int(data["top"][i]),
                "width": int(data["width"][i]),
                "height": int(data["height"][i]),
                "actionable": False,
            })
        return result
