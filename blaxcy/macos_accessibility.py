from __future__ import annotations

import re
from typing import Any


def snapshot() -> list[dict[str, Any]]:
    """Best-effort macOS Accessibility API adapter.

    Requires PyObjC and Accessibility permission. Position/size values are
    parsed without calling AXValueGetValue because some PyObjC versions have
    unsafe edge cases around that low-level out-parameter API.
    """
    try:
        import Quartz
    except ImportError:
        return []

    result: list[dict[str, Any]] = []
    try:
        system = Quartz.AXUIElementCreateSystemWide()
        err, focused = Quartz.AXUIElementCopyAttributeValue(
            system, Quartz.kAXFocusedApplicationAttribute, None
        )
        if err != Quartz.kAXErrorSuccess or focused is None:
            return result
    except Exception:
        return result

    def attr(element: Any, key: str) -> Any:
        try:
            err, value = Quartz.AXUIElementCopyAttributeValue(element, key, None)
            return value if err == Quartz.kAXErrorSuccess else None
        except Exception:
            return None

    def point(value: Any) -> tuple[float, float] | None:
        if value is None:
            return None
        try:
            x, y = float(value.x), float(value.y)
            return x, y
        except Exception:
            pass
        match = re.search(r"x[:=]\s*([-+]?\d+(?:\.\d+)?).*?y[:=]\s*([-+]?\d+(?:\.\d+)?)", str(value), re.I)
        return (float(match.group(1)), float(match.group(2))) if match else None

    def size(value: Any) -> tuple[float, float] | None:
        if value is None:
            return None
        try:
            return float(value.width), float(value.height)
        except Exception:
            pass
        match = re.search(r"w(?:idth)?[:=]\s*([-+]?\d+(?:\.\d+)?).*?h(?:eight)?[:=]\s*([-+]?\d+(?:\.\d+)?)", str(value), re.I)
        return (float(match.group(1)), float(match.group(2))) if match else None

    def walk(element: Any, depth: int = 0) -> None:
        if depth > 16 or len(result) >= 500:
            return

        role = attr(element, Quartz.kAXRoleAttribute)
        title = attr(element, Quartz.kAXTitleAttribute) or attr(
            element, Quartz.kAXDescriptionAttribute
        )
        pos = point(attr(element, Quartz.kAXPositionAttribute))
        extent = size(attr(element, Quartz.kAXSizeAttribute))

        if role and pos and extent and extent[0] > 0 and extent[1] > 0:
            role_name = str(role)
            result.append({
                "type": "accessibility",
                "role": role_name,
                "name": str(title or ""),
                "x": int(pos[0]),
                "y": int(pos[1]),
                "width": int(extent[0]),
                "height": int(extent[1]),
                "actionable": role_name.lower() in {
                    "axbutton", "axcheckbox", "axtextfield", "axcombobox",
                    "axlink", "axmenuitem", "axtab", "axradiobutton",
                },
            })

        children = attr(element, Quartz.kAXChildrenAttribute) or []
        for child in list(children)[:500]:
            walk(child, depth + 1)

    walk(focused)
    return result
