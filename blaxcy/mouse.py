from __future__ import annotations

import pyautogui


def move(x: int, y: int) -> None:
    pyautogui.moveTo(x, y, duration=0)


def click(x: int, y: int, button: str = "left", clicks: int = 1) -> None:
    if button not in {"left", "middle", "right"}:
        raise ValueError("unsupported mouse button")
    if not 1 <= clicks <= 3:
        raise ValueError("click count must be 1..3")
    pyautogui.click(x=x, y=y, button=button, clicks=clicks, interval=0.03)


def scroll(x: int, y: int, amount: int) -> None:
    pyautogui.moveTo(x, y, duration=0)
    pyautogui.scroll(amount)
