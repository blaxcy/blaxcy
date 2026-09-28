from __future__ import annotations

import argparse
import signal
import threading

import pyautogui

from .connect import run_connect
from .eye import Eye, EyeConfig
from .github_control import GitHubMailbox, config_from_env


def main() -> None:
    parser = argparse.ArgumentParser(prog="blaxcy")
    sub = parser.add_subparsers(dest="command", required=True)

    connect = sub.add_parser("connect", help="start temporary foreground device session")
    connect.add_argument("--fps", type=int, default=60)
    connect.add_argument("--ocr", action="store_true")
    connect.add_argument("--host", default="127.0.0.1")
    connect.add_argument("--port", type=int, default=8765)
    connect.add_argument("--pairing-file", default=".blaxcy/pairing.json")
    connect.add_argument("--quiet", action="store_true")

    bridge = sub.add_parser(
        "github-bridge",
        help="run EYE and receive structured commands through the GitHub control plane",
    )
    bridge.add_argument("--poll", type=float, default=None)
    bridge.add_argument("--fps", type=int, default=30)
    bridge.add_argument("--ocr", action="store_true")

    args = parser.parse_args()

    if args.command == "connect":
        raise SystemExit(run_connect(
            args.fps, args.ocr, args.host, args.port, args.pairing_file, args.quiet
        ))

    if args.command == "github-bridge":
        from dataclasses import replace

        stop_event = threading.Event()
        cfg = config_from_env()
        if args.poll is not None:
            cfg = replace(cfg, poll_seconds=max(2.0, args.poll))

        mailbox = GitHubMailbox(cfg)
        width, height = map(int, pyautogui.size())

        worker = threading.Thread(
            target=mailbox.run,
            args=(width, height, stop_event.is_set),
            daemon=True,
            name="blaxcy-github-control",
        )
        worker.start()

        def stop(*_args) -> None:
            stop_event.set()

        signal.signal(signal.SIGINT, stop)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, stop)

        Eye(EyeConfig(target_fps=args.fps, ocr=args.ocr)).run(
            lambda message: print(message, flush=True),
            stop_event.is_set,
        )


if __name__ == "__main__":
    main()
