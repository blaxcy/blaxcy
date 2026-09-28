from __future__ import annotations

import pyautogui


def press(key: str) -> None:
    pyautogui.press(key)


def hotkey(*keys: str) -> None:
    if not keys:
        raise ValueError("hotkey requires at least one key")
    pyautogui.hotkey(*keys)


def type_text(text: str) -> None:
    if len(text) > 10000:
        raise ValueError("text payload too large")
    pyautogui.write(text, interval=0)
