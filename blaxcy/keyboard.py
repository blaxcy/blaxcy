from __future__ import annotations


def _pyautogui():
    import pyautogui
    return pyautogui


def press(key: str) -> None:
    _pyautogui().press(key)


def hotkey(*keys: str) -> None:
    _pyautogui().hotkey(*keys)


def type_text(text: str) -> None:
    _pyautogui().write(text, interval=0)
