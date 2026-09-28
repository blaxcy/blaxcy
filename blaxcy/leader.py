from __future__ import annotations

"""BLAXCY Leader: compact, state-aware command execution layer."""

from dataclasses import dataclass
from typing import Any, Callable

from .commands import CommandError, execute


@dataclass(frozen=True)
class Leader:
    state_provider: Callable[[], dict[str, Any]]

    def execute(self, command: str, width: int, height: int) -> dict[str, Any]:
        raw = command.strip()
        if not raw:
            raise CommandError("empty leader command")

        head, _, tail = raw.partition(" ")
        verb = head.casefold()
        tail = tail.strip()

        if verb in {"click", "tap"}:
            x, y = self.resolve_target(tail)
            return execute({"type":"command","action":"mouse.click","x":x,"y":y}, width, height)

        if verb == "move":
            x, y = self.resolve_target(tail)
            return execute({"type":"command","action":"mouse.move","x":x,"y":y}, width, height)

        if verb == "scroll":
            try:
                amount = int(tail)
            except ValueError as exc:
                raise CommandError("scroll requires an integer") from exc
            return execute({"type":"command","action":"mouse.scroll","amount":amount}, width, height)

        if verb == "press":
            if not tail:
                raise CommandError("press requires a key")
            return execute({"type":"command","action":"keyboard.press","key":tail}, width, height)

        if verb == "hotkey":
            keys = tail.split()
            if not keys:
                raise CommandError("hotkey requires keys")
            return execute({"type":"command","action":"keyboard.hotkey","keys":keys}, width, height)

        if verb in {"type","write"}:
            if not tail:
                raise CommandError("type requires text")
            return execute({"type":"command","action":"keyboard.type","text":tail}, width, height)

        raise CommandError("unsupported leader command")

    def resolve_target(self, target: str) -> tuple[int, int]:
        if not target:
            raise CommandError("target required; use element id, text, or x,y")

        if "," in target:
            a, b = (part.strip() for part in target.split(",", 1))
            if a.lstrip("-").isdigit() and b.lstrip("-").isdigit():
                return int(a), int(b)

        state = self.state_provider() or {}
        elements = state.get("elements") or []

        exact = [e for e in elements if str(e.get("id","")) == target]
        if len(exact) == 1:
            return self._center(exact[0])

        q = target.casefold()
        matches = []
        for e in elements:
            values = [
                str(e.get("name","")),
                str(e.get("text","")),
                str(e.get("role","")),
                str(e.get("value","")),
            ]
            if any(q == v.casefold() or q in v.casefold() for v in values if v):
                matches.append(e)

        if len(matches) == 1:
            return self._center(matches[0])
        if len(matches) > 1:
            raise CommandError("target is ambiguous; use the EYE element id")
        raise CommandError("target not found in current EYE state")

    @staticmethod
    def _center(element: dict[str, Any]) -> tuple[int, int]:
        try:
            return (
                int(element["x"]) + int(element["width"]) // 2,
                int(element["y"]) + int(element["height"]) // 2,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CommandError("target has invalid geometry") from exc
