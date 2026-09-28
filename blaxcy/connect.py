from __future__ import annotations

import argparse
import signal
import threading

from .eye import Eye, EyeConfig
from .protocol import encode, event, session_token


class Runtime:
    def __init__(self, fps: int):
        self.stop_event = threading.Event()
        self.eye = Eye(EyeConfig(target_fps=fps))
        self.token = session_token()

    def stop(self, *_args) -> None:
        self.stop_event.set()

    def emit(self, message: dict) -> None:
        print(encode(message), flush=True)


def run_connect(fps: int) -> int:
    runtime = Runtime(fps)

    signal.signal(signal.SIGINT, runtime.stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, runtime.stop)

    runtime.emit(event(
        "session.started",
        session="foreground",
        capabilities=["eye", "mouse", "keyboard"],
        token=runtime.token,
    ))

    try:
        runtime.eye.run(runtime.emit, runtime.stop_event.is_set)
    finally:
        runtime.emit(event("session.stopped"))

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="blaxcy")
    sub = parser.add_subparsers(dest="command", required=True)

    connect = sub.add_parser("connect", help="start the temporary foreground device session")
    connect.add_argument("--fps", type=int, default=60)

    args = parser.parse_args()
    if args.command == "connect":
        raise SystemExit(run_connect(args.fps))
