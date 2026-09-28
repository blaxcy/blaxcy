from __future__ import annotations

import argparse
import threading

from .commands import execute
from .connect import run_connect
from .github_bridge import GitHubBridge, config_from_env


def main() -> None:
    parser = argparse.ArgumentParser(prog="blaxcy")
    sub = parser.add_subparsers(dest="command", required=True)

    connect = sub.add_parser("connect", help="start temporary foreground device session")
    connect.add_argument("--fps", type=int, default=60)
    connect.add_argument("--ocr", action="store_true")
    connect.add_argument("--host", default="127.0.0.1")
    connect.add_argument("--port", type=int, default=8765)

    bridge = sub.add_parser("github-bridge", help="use a GitHub Issue as the device control mailbox")
    bridge.add_argument("--poll", type=float, default=None)

    args = parser.parse_args()

    if args.command == "connect":
        raise SystemExit(run_connect(args.fps, args.ocr, args.host, args.port))

    if args.command == "github-bridge":
        from dataclasses import replace
        import pyautogui
        from .eye import Eye, EyeConfig

        stop_event = threading.Event()
        latest: dict = {}

        def emit(message: dict) -> None:
            nonlocal latest
            if message.get("type") in {"eye.keyframe", "eye.delta", "eye.cursor"}:
                latest = message
            print(message, flush=True)

        cfg = config_from_env()
        if args.poll is not None:
            cfg = replace(cfg, poll_seconds=max(0.5, args.poll))

        bridge = GitHubBridge(
            cfg,
            execute_command=lambda command: execute(
                command, int(pyautogui.size().width), int(pyautogui.size().height)
            ),
            state_provider=lambda: latest,
        )

        worker = threading.Thread(
            target=bridge.run, args=(stop_event.is_set,), daemon=True
        )
        worker.start()

        try:
            Eye(EyeConfig(ocr=False)).run(emit, stop_event.is_set)
        except KeyboardInterrupt:
            pass
        finally:
            stop_event.set()


if __name__ == "__main__":
    main()
