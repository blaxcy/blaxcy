from __future__ import annotations

from typing import Any


def snapshot() -> list[dict[str, Any]]:
    """Best-effort macOS AX snapshot.

    Uses Quartz accessibility APIs when available. macOS may require the
    terminal/Python process to be granted Accessibility permission.
    """
    try:
        import Quartz
    except ImportError:
        return []

    app = Quartz.AXUIElementCreateSystemWide()
    result: list[dict[str, Any]] = []
    _walk(Quartz, app, result, 0)
    return result


def _value(Quartz: Any, element: Any, attribute: str) -> Any:
    try:
        status, value = Quartz.AXUIElementCopyAttributeValue(element, attribute, None)
        if status == Quartz.kAXErrorSuccess:
            return value
    except Exception:
        pass
    return None


def _walk(Quartz: Any, element: Any, out: list[dict[str, Any]], depth: int) -> None:
    if depth > 14 or len(out) >= 500:
        return

    role = _value(Quartz, element, "AXRole") or "unknown"
    title = _value(Quartz, element, "AXTitle") or _value(Quartz, element, "AXDescription") or ""
    position = _value(Quartz, element, "AXPosition")
    size = _value(Quartz, element, "AXSize")

    try:
        x, y = int(position.x), int(position.y)
        w, h = int(size.width), int(size.height)
    except Exception:
        x = y = w = h = 0

    actionable_roles = {
        "AXButton", "AXCheckBox", "AXRadioButton", "AXComboBox", "AXTextField",
        "AXTextArea", "AXMenuItem", "AXLink", "AXTab", "AXPopUpButton",
        "AXSlider", "AXIncrementor", "AXDisclosureTriangle",
    }

    if w > 0 and h > 0:
        out.append({
            "type": "accessibility",
            "role": str(role),
            "name": str(title),
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "actionable": str(role) in actionable_roles,
            "enabled": bool(_value(Quartz, element, "AXEnabled") is not False),
            "focused": bool(_value(Quartz, element, "AXFocused") is True),
        })

    children = _value(Quartz, element, "AXChildren") or []
    for child in children:
        _walk(Quartz, child, out, depth + 1)
