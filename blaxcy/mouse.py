from __future__ import annotations

from typing import Optional

import pyautogui


def move(x: int, y: int, duration: float = 0.0) -> None:
    pyautogui.moveTo(x, y, duration=max(0.0, min(float(duration), 2.0)))


def click(x: int, y: int, button: str = "left", clicks: int = 1) -> None:
    if button not in {"left", "middle", "right"}:
        raise ValueError("unsupported mouse button")
    if clicks not in {1, 2, 3}:
        raise ValueError("clicks must be 1..3")
    pyautogui.click(x=x, y=y, clicks=clicks, button=button)


def scroll(x: Optional[int], y: Optional[int], amount: int) -> None:
    if x is not None and y is not None:
        pyautogui.moveTo(x, y)
    pyautogui.scroll(amount)
