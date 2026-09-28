from __future__ import annotations

import argparse
import asyncio
import signal
import threading

import mss

from .eye import Eye, EyeConfig
from .protocol import encode, event, session_token
from .transport import LocalTransport


class Runtime:
    def __init__(self, fps: int, ocr: bool, host: str, port: int):
        self.stop_event = threading.Event()
        self.eye = Eye(EyeConfig(target_fps=fps, ocr=ocr))
        self.token = session_token()
        self.host = host
        self.port = port
        self.latest_state: dict = {}
        self.transport: LocalTransport | None = None

    def stop(self, *_args) -> None:
        self.stop_event.set()

    def emit(self, message: dict) -> None:
        if message.get("type") == "eye.keyframe":
            self.latest_state = message
        if self.transport is not None:
            self.transport.publish(message)
        print(encode(message), flush=True)


def run_connect(fps: int, ocr: bool, host: str, port: int) -> int:
    runtime = Runtime(fps, ocr, host, port)
    signal.signal(signal.SIGINT, runtime.stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, runtime.stop)

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        size = (int(monitor["width"]), int(monitor["height"]))

    runtime.transport = LocalTransport(runtime.token, lambda: runtime.latest_state, lambda: size)

    server_thread = threading.Thread(
        target=lambda: asyncio.run(runtime.transport.serve(host, port)),
        daemon=True,
        name="blaxcy-transport",
    )
    server_thread.start()
    if not runtime.transport.wait_ready():
        raise RuntimeError("transport failed to start")

    runtime.emit(event(
        "session.started",
        session="foreground",
        capabilities=["eye", "mouse", "keyboard"],
        transport={"scheme": "ws", "host": host, "port": port},
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

    connect = sub.add_parser("connect", help="start temporary foreground device session")
    connect.add_argument("--fps", type=int, default=60)
    connect.add_argument("--ocr", action="store_true")
    connect.add_argument("--host", default="127.0.0.1")
    connect.add_argument("--port", type=int, default=8765)

    args = parser.parse_args()
    if args.command == "connect":
        raise SystemExit(run_connect(args.fps, args.ocr, args.host, args.port))
