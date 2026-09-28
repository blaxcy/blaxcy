from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import signal
import threading
import time
from pathlib import Path

import mss

from .eye import Eye, EyeConfig
from .protocol import encode, event, session_token
from .transport import LocalTransport


def _write_pairing(path: str, token: str, session_id: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "device_id": os.environ.get("BLAXCY_DEVICE_ID") or secrets.token_hex(12),
        "session_id": session_id,
        "token": token,
        "created_at": time.time(),
        "protocol": "blaxcy/0.1",
    }
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    tmp.replace(p)


class Runtime:
    def __init__(self, fps: int, ocr: bool, host: str, port: int, pairing_file: str):
        self.stop_event = threading.Event()
        self.eye = Eye(EyeConfig(target_fps=fps, ocr=ocr))
        self.token = session_token()
        self.session_id = secrets.token_urlsafe(18)
        self.host = host
        self.port = port
        self.pairing_file = pairing_file
        self.latest_state: dict = {}
        self.events: list[dict] = []
        self.transport: LocalTransport | None = None

    def stop(self, *_args) -> None:
        self.stop_event.set()

    def emit(self, message: dict) -> None:
        if message.get("type") == "eye.keyframe":
            # latest_state must remain a complete state. Deltas are retained
            # separately so MCP eye_state never accidentally returns a patch.
            self.latest_state = message
            self.events.append(message)
            self.events = self.events[-512:]
        elif message.get("type") in {"eye.delta", "eye.cursor"}:
            self.events.append(message)
            self.events = self.events[-512:]
        if self.transport is not None:
            self.transport.publish(message)
        print(encode(message), flush=True)


def run_connect(fps: int, ocr: bool, host: str, port: int, pairing_file: str, quiet: bool = False) -> int:
    runtime = Runtime(fps, ocr, host, port, pairing_file)
    _write_pairing(pairing_file, runtime.token, runtime.session_id)
    signal.signal(signal.SIGINT, runtime.stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, runtime.stop)

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        size = (int(monitor["width"]), int(monitor["height"]))

    runtime.transport = LocalTransport(
        runtime.token,
        lambda: runtime.latest_state,
        lambda: size,
        lambda revision, limit: [e for e in runtime.events if int(e.get("revision", 0)) > revision][-limit:],
    )

    server_thread = threading.Thread(
        target=lambda: asyncio.run(runtime.transport.serve(host, port)),
        daemon=True,
        name="blaxcy-transport",
    )
    server_thread.start()
    if not runtime.transport.wait_ready():
        raise RuntimeError("transport failed to start")

    started = event(
        "session.started",
        session=runtime.session_id,
        capabilities=["eye", "mouse", "keyboard"],
        transport={"scheme": "ws", "host": host, "port": port},
    )
    if not quiet:
        runtime.emit(started)

    try:
        runtime.eye.run(runtime.emit, runtime.stop_event.is_set)
    finally:
        if not quiet:
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
    connect.add_argument("--pairing-file", default=os.environ.get("BLAXCY_PAIRING_FILE", ".blaxcy/pairing.json"))
    connect.add_argument("--quiet", action="store_true")

    args = parser.parse_args()
    if args.command == "connect":
        raise SystemExit(run_connect(
            args.fps, args.ocr, args.host, args.port, args.pairing_file, args.quiet
        ))
