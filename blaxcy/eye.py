from __future__ import annotations

import base64
import hashlib
import time
from dataclasses import dataclass
from typing import Callable

import cv2
import mss
import numpy as np
import pyautogui

from .protocol import event
from .semantic import SemanticAnalyzer, SemanticConfig
from .state import ScreenState


@dataclass
class EyeConfig:
    target_fps: int = 60
    change_threshold: int = 12
    min_changed_area: int = 16
    keyframe_every: float = 5.0
    ocr: bool = False
    max_regions: int = 24
    region_padding: int = 4
    jpeg_quality: int = 78
    max_region_pixels: int = 1_000_000
    max_delta_bytes: int = 4_000_000
    keyframe_on_large_change: float = 0.35
    semantic_every: float = 5.0


class Eye:
    """Continuous local screen perception with visual deltas and semantic keyframes."""

    def __init__(self, config: EyeConfig | None = None):
        self.config = config or EyeConfig()
        self._previous_gray: np.ndarray | None = None
        self._last_keyframe = 0.0
        self._last_semantic = 0.0
        self._state: ScreenState | None = None
        self._semantic = SemanticAnalyzer(SemanticConfig(ocr=self.config.ocr))

    def run(self, emit: Callable[[dict], None], stop: Callable[[], bool]) -> None:
        interval = 1.0 / max(1, self.config.target_fps)
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            width, height = int(monitor["width"]), int(monitor["height"])
            self._state = ScreenState(width=width, height=height)

            while not stop():
                started = time.perf_counter()
                raw = np.asarray(sct.grab(monitor))
                frame = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                frame_hash = hashlib.blake2b(frame, digest_size=16).hexdigest()
                cursor = pyautogui.position()
                cursor_state = {"x": int(cursor.x), "y": int(cursor.y)}
                now = time.monotonic()

                if self._previous_gray is None:
                    self._previous_gray = gray
                    self._state.cursor = cursor_state
                    self._state.last_frame_hash = frame_hash
                    self._refresh_semantics(frame)
                    self._last_keyframe = self._last_semantic = now
                    self._emit_keyframe(emit, frame)
                else:
                    self._process_change(frame, gray, frame_hash, cursor_state, emit)

                    if now - self._last_semantic >= self.config.semantic_every:
                        self._refresh_semantics(frame)
                        self._last_semantic = now
                        self._state.last_frame_hash = frame_hash
                        self._emit_keyframe(emit, frame)
                        self._last_keyframe = now

                self._previous_gray = gray
                remaining = interval - (time.perf_counter() - started)
                if remaining > 0:
                    time.sleep(remaining)

    def _refresh_semantics(self, frame: np.ndarray) -> None:
        assert self._state is not None
        self._state.elements = self._semantic.analyze(frame)
        self._state.revision += 1

    def _encode_jpeg(self, image: np.ndarray) -> str | None:
        ok, encoded = cv2.imencode(
            ".jpg", image,
            [cv2.IMWRITE_JPEG_QUALITY, max(35, min(95, self.config.jpeg_quality))],
        )
        if not ok:
            return None
        return base64.b64encode(encoded.tobytes()).decode("ascii")

    def _emit_keyframe(self, emit: Callable[[dict], None], frame: np.ndarray) -> None:
        assert self._state is not None
        payload = self._encode_jpeg(frame)
        emit(event(
            "eye.keyframe",
            revision=self._state.revision,
            screen={"width": self._state.width, "height": self._state.height},
            elements=self._state.elements,
            cursor=self._state.cursor,
            frame_hash=self._state.last_frame_hash,
            image={"encoding": "jpeg", "data": payload} if payload else None,
        ))

    def _process_change(
        self,
        frame: np.ndarray,
        gray: np.ndarray,
        frame_hash: str,
        cursor_state: dict[str, int],
        emit: Callable[[dict], None],
    ) -> None:
        assert self._previous_gray is not None
        assert self._state is not None

        diff = cv2.absdiff(gray, self._previous_gray)
        mask = (diff >= self.config.change_threshold).astype(np.uint8) * 255
        changed = int(cv2.countNonZero(mask))
        total = gray.shape[0] * gray.shape[1]
        changed_ratio = changed / max(1, total)

        if cursor_state != self._state.cursor:
            self._state.cursor = cursor_state
            self._state.revision += 1
            emit(event("eye.cursor", revision=self._state.revision, cursor=cursor_state))

        if changed < self.config.min_changed_area:
            return

        if changed_ratio >= self.config.keyframe_on_large_change:
            self._state.revision += 1
            self._state.last_frame_hash = frame_hash
            self._last_keyframe = time.monotonic()
            self._emit_keyframe(emit, frame)
            return

        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        regions: list[dict[str, int | str]] = []
        encoded_bytes = 0
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[: self.config.max_regions]:
            x, y, w, h = cv2.boundingRect(contour)
            x = max(0, x - self.config.region_padding)
            y = max(0, y - self.config.region_padding)
            x2 = min(frame.shape[1], x + w + 2 * self.config.region_padding)
            y2 = min(frame.shape[0], y + h + 2 * self.config.region_padding)
            w, h = x2 - x, y2 - y
            if w * h < self.config.min_changed_area or w * h > self.config.max_region_pixels:
                continue
            encoded = self._encode_jpeg(frame[y:y2, x:x2])
            if not encoded:
                continue
            encoded_bytes += len(encoded)
            if encoded_bytes > self.config.max_delta_bytes:
                break
            regions.append({
                "x": x, "y": y, "width": w, "height": h,
                "encoding": "jpeg", "data": encoded,
            })

        if not regions:
            return

        self._state.revision += 1
        self._state.last_frame_hash = frame_hash
        emit(event(
            "eye.delta",
            revision=self._state.revision,
            changed_pixels=changed,
            changed_ratio=round(changed_ratio, 6),
            regions=regions,
            confidence="pixel-delta+visual",
            frame_hash=frame_hash,
        ))
