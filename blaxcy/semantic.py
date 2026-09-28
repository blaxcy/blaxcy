from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass
class SemanticConfig:
    ocr: bool = False
    max_elements: int = 500


class SemanticAnalyzer:
    """Best-effort UI perception layer.

    It combines OCR (when enabled/installed) with simple visual geometry.
    Platform accessibility adapters can replace/augment this analyzer later.
    """

    def __init__(self, config: SemanticConfig | None = None):
        self.config = config or SemanticConfig()

    def analyze(self, frame_bgr: np.ndarray) -> list[dict[str, Any]]:
        h, w = frame_bgr.shape[:2]
        elements: list[dict[str, Any]] = []

        if self.config.ocr:
            elements.extend(self._ocr(frame_bgr))

        # Keep deterministic IDs for the same ordered observation.
        for i, element in enumerate(elements[: self.config.max_elements], 1):
            element["id"] = f"e{i}"
            element["screen"] = {
                "x": element["x"], "y": element["y"],
                "width": element["width"], "height": element["height"],
            }

        return elements

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
        n = len(data.get("text", []))
        for i in range(n):
            text = str(data["text"][i]).strip()
            try:
                conf = float(data["conf"][i])
            except (TypeError, ValueError):
                conf = -1
            if not text or conf < 20:
                continue
            x, y = int(data["left"][i]), int(data["top"][i])
            w, h = int(data["width"][i]), int(data["height"][i])
            result.append({
                "type": "text",
                "text": text,
                "confidence": round(conf / 100.0, 3),
                "x": x, "y": y, "width": w, "height": h,
                "actionable": False,
            })
        return result
