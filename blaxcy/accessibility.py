from __future__ import annotations

import platform
from typing import Any


class AccessibilityProvider:
    """Optional native accessibility/UI-tree provider.

    Providers are best-effort and never replace pixel/OCR perception.
    """

    def snapshot(self) -> list[dict[str, Any]]:
        system = platform.system()
        if system == "Windows":
            return self._windows()
        if system == "Darwin":
            return self._macos()
        if system == "Linux":
            return self._linux()
        return []

    def _windows(self) -> list[dict[str, Any]]:
        try:
            from pywinauto import Desktop
        except ImportError:
            return []

        result: list[dict[str, Any]] = []
        try:
            for win in Desktop(backend="uia").windows():
                self._walk_windows(win, result, 0)
        except Exception:
            return result
        return result

    def _walk_windows(self, node: Any, out: list[dict[str, Any]], depth: int) -> None:
        if depth > 12 or len(out) >= 500:
            return
        try:
            rect = node.rectangle()
            info = {
                "type": "accessibility",
                "role": str(node.element_info.control_type or "unknown"),
                "name": str(node.window_text() or ""),
                "x": int(rect.left),
                "y": int(rect.top),
                "width": max(0, int(rect.width())),
                "height": max(0, int(rect.height())),
                "actionable": str(node.element_info.control_type or "").lower()
                in {"button", "edit", "checkbox", "combobox", "menuitem", "tab", "hyperlink"},
            }
            if info["width"] > 0 and info["height"] > 0:
                out.append(info)
        except Exception:
            pass
        try:
            for child in node.children():
                self._walk_windows(child, out, depth + 1)
        except Exception:
            return

    def _linux(self) -> list[dict[str, Any]]:
        try:
            import pyatspi
        except ImportError:
            return []

        result: list[dict[str, Any]] = []

        def walk(node: Any, depth: int) -> None:
            if depth > 16 or len(result) >= 500:
                return
            try:
                comp = node.queryComponent()
                x, y, w, h = comp.getExtents(pyatspi.DESKTOP_COORDS)
                role = node.getRoleName() or "unknown"
                name = node.name or ""
                state = node.getState()
                actionable = any(
                    getattr(state, flag, False)
                    for flag in ("contains", "focusable", "selectable")
                ) or role.lower() in {
                    "push button", "toggle button", "text", "entry", "check box",
                    "combo box", "menu item", "page tab", "link",
                }
                if w > 0 and h > 0:
                    result.append({
                        "type": "accessibility",
                        "role": role,
                        "name": name,
                        "x": int(x), "y": int(y), "width": int(w), "height": int(h),
                        "actionable": bool(actionable),
                    })
            except Exception:
                pass
            try:
                for i in range(node.childCount):
                    walk(node.getChildAtIndex(i), depth + 1)
            except Exception:
                return

        try:
            desktop = pyatspi.Registry.getDesktop(0)
            walk(desktop, 0)
        except Exception:
            return result
        return result

    def _macos(self) -> list[dict[str, Any]]:
        # AXUIElement access is intentionally optional; keep the base package
        # dependency-free on macOS and let a platform adapter supply it.
        try:
            from .macos_accessibility import snapshot
        except ImportError:
            return []
        try:
            return snapshot()
        except Exception:
            return []
