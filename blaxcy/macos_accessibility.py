from __future__ import annotations

from typing import Any


def snapshot() -> list[dict[str, Any]]:
    """Best-effort macOS Accessibility API adapter.

    Requires PyObjC (Quartz) and the user granting Accessibility permission
    to the running Python application.
    """
    try:
        import Quartz
    except ImportError:
        return []

    result: list[dict[str, Any]] = []
    system = Quartz.AXUIElementCreateSystemWide()
    err, focused = Quartz.AXUIElementCopyAttributeValue(
        system, Quartz.kAXFocusedApplicationAttribute, None
    )
    if err != Quartz.kAXErrorSuccess or focused is None:
        return result

    def attr(element: Any, key: str) -> Any:
        err, value = Quartz.AXUIElementCopyAttributeValue(element, key, None)
        return value if err == Quartz.kAXErrorSuccess else None

    def walk(element: Any, depth: int = 0) -> None:
        if depth > 16 or len(result) >= 500:
            return
        role = attr(element, Quartz.kAXRoleAttribute)
        title = attr(element, Quartz.kAXTitleAttribute) or attr(element, Quartz.kAXDescriptionAttribute)
        pos = attr(element, Quartz.kAXPositionAttribute)
        size = attr(element, Quartz.kAXSizeAttribute)
        if role:
            try:
                p = Quartz.CGPoint()
                s = Quartz.CGSize()
                Quartz.AXValueGetValue(pos, Quartz.kAXValueCGPointType, p)
                Quartz.AXValueGetValue(size, Quartz.kAXValueCGSizeType, s)
                result.append({
                    "type": "accessibility",
                    "role": str(role),
                    "name": str(title or ""),
                    "x": int(p.x), "y": int(p.y),
                    "width": int(s.width), "height": int(s.height),
                    "actionable": str(role).lower() in {
                        "axbutton", "axcheckbox", "axtextfield", "axcombobox",
                        "axlink", "axmenuitem", "axtab",
                    },
                })
            except Exception:
                pass
        children = attr(element, Quartz.kAXChildrenAttribute) or []
        for child in children:
            walk(child, depth + 1)

    walk(focused)
    return result
