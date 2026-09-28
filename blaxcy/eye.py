from __future__ import annotations

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


class Eye:
    """Continuous screen feed with persistent state and semantic keyframes."""

    def __init__(self, config: EyeConfig | None = None):
        self.config = config or EyeConfig()
        self._previous_gray: np.ndarray | None = None
        self._last_keyframe = 0.0
        self._state: ScreenState | None = None
        self._semantic = SemanticAnalyzer(SemanticConfig(ocr=self.config.ocr))

    def run(self, emit: Callable[[dict], None], stop: Callable[[], bool]) -> None:
        interval = 1.0 / max(1, self.config.target_fps)

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            width = int(monitor["width"])
            height = int(monitor["height"])
            self._state = ScreenState(width=width, height=height)

            while not stop():
                started = time.perf_counter()
                raw = np.asarray(sct.grab(monitor))
                frame = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                cursor = pyautogui.position()
                self._state.cursor = {"x": int(cursor.x), "y": int(cursor.y)}

                if self._previous_gray is None:
                    self._previous_gray = gray
                    self._state.elements = self._semantic.analyze(frame)
                    self._state.revision += 1
                    self._last_keyframe = time.monotonic()
                    self._emit_keyframe(emit)
                else:
                    self._process_change(gray, emit)

                self._previous_gray = gray

                if time.monotonic() - self._last_keyframe >= self.config.keyframe_every:
                    self._state.elements = self._semantic.analyze(frame)
                    self._state.revision += 1
                    self._last_keyframe = time.monotonic()
                    self._emit_keyframe(emit)

                remaining = interval - (time.perf_counter() - started)
                if remaining > 0:
                    time.sleep(remaining)

    def _emit_keyframe(self, emit: Callable[[dict], None]) -> None:
        assert self._state is not None
        emit(event(
            "eye.keyframe",
            revision=self._state.revision,
            screen={"width": self._state.width, "height": self._state.height},
            elements=self._state.elements,
            cursor=self._state.cursor,
        ))

    def _process_change(self, gray: np.ndarray, emit: Callable[[dict], None]) -> None:
        assert self._previous_gray is not None
        assert self._state is not None

        diff = cv2.absdiff(gray, self._previous_gray)
        mask = (diff >= self.config.change_threshold).astype(np.uint8) * 255
        changed = int(cv2.countNonZero(mask))

        cursor = pyautogui.position()
        cursor_state = {"x": int(cursor.x), "y": int(cursor.y)}
        cursor_changed = cursor_state != self._state.cursor
        if cursor_changed:
            self._state.cursor = cursor_state
            self._state.revision += 1
            emit(event("eye.cursor", revision=self._state.revision, cursor=cursor_state))

        if changed < self.config.min_changed_area:
            return

        mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        regions: list[dict[str, int]] = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w * h >= self.config.min_changed_area:
                regions.append({"x": x, "y": y, "width": w, "height": h})

        if not regions:
            return

        self._state.revision += 1
        emit(event(
            "eye.delta",
            revision=self._state.revision,
            changed_pixels=changed,
            regions=regions,
            confidence="pixel-delta",
        ))
